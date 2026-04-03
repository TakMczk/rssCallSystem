#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import tempfile
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys

from openai import AsyncOpenAI as BaseAsyncOpenAI

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import config, scorer  # noqa: E402
from src.fetcher import fetch_all_feeds, normalize  # noqa: E402
from src.model_benchmark import (  # noqa: E402
    estimate_cost_usd,
    fallback_rate,
    mean_absolute_total_gap,
    pearson_total_correlation,
    select_representative_articles,
    summary_in_target_rate,
)
from src.models import Article, ScoreResult  # noqa: E402


@dataclass
class UsageMetrics:
    model: str
    api_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0

    def record(self, response) -> None:
        usage = getattr(response, "usage", None)
        if usage is None:
            return

        self.api_calls += 1
        self.input_tokens += int(
            getattr(usage, "prompt_tokens", None)
            or getattr(usage, "input_tokens", None)
            or 0
        )
        self.output_tokens += int(
            getattr(usage, "completion_tokens", None)
            or getattr(usage, "output_tokens", None)
            or 0
        )

        completion_details = getattr(usage, "completion_tokens_details", None)
        if completion_details is not None:
            self.reasoning_tokens += int(
                getattr(completion_details, "reasoning_tokens", None) or 0
            )

        output_details = getattr(usage, "output_tokens_details", None)
        if output_details is not None:
            self.reasoning_tokens += int(
                getattr(output_details, "reasoning_tokens", None) or 0
            )


@dataclass
class BenchmarkResult:
    model: str
    reasoning_effort: str | None
    elapsed_seconds: float
    scores: list[ScoreResult]
    usage: UsageMetrics

    @property
    def estimated_cost_usd(self) -> float:
        return estimate_cost_usd(
            self.model, self.usage.input_tokens, self.usage.output_tokens
        )


class InstrumentedCompletions:
    def __init__(self, completions, metrics: UsageMetrics):
        self._completions = completions
        self._metrics = metrics

    async def create(self, **kwargs):
        response = await self._completions.create(**kwargs)
        self._metrics.record(response)
        return response


class InstrumentedChat:
    def __init__(self, chat, metrics: UsageMetrics):
        self.completions = InstrumentedCompletions(chat.completions, metrics)


def make_instrumented_async_openai(metrics: UsageMetrics):
    class InstrumentedAsyncOpenAI:
        def __init__(self, *args, **kwargs):
            client = BaseAsyncOpenAI(*args, **kwargs)
            self.chat = InstrumentedChat(client.chat, metrics)

    return InstrumentedAsyncOpenAI


async def load_articles(limit: int) -> list[Article]:
    raw_items = await fetch_all_feeds(config.FEED_URLS)
    articles = normalize(raw_items)
    return select_representative_articles(articles, limit)


async def run_model(
    articles: list[Article],
    *,
    model: str,
    reasoning_effort: str | None,
) -> BenchmarkResult:
    original_model = config.OPENAI_MODEL
    original_effort = config.OPENAI_REASONING_EFFORT
    original_async_openai = scorer.AsyncOpenAI
    original_cache_file = scorer.CACHE_FILE
    original_cache = dict(scorer._cache)

    usage = UsageMetrics(model=model)
    scorer.AsyncOpenAI = make_instrumented_async_openai(usage)
    config.OPENAI_MODEL = model
    config.OPENAI_REASONING_EFFORT = reasoning_effort

    with tempfile.TemporaryDirectory() as temp_dir:
        scorer.CACHE_FILE = Path(temp_dir) / "scores.jsonl"
        scorer._cache.clear()
        start = time.perf_counter()
        try:
            scores = await scorer.score_articles(articles)
        finally:
            elapsed = time.perf_counter() - start
            scorer.AsyncOpenAI = original_async_openai
            scorer.CACHE_FILE = original_cache_file
            scorer._cache.clear()
            scorer._cache.update(original_cache)
            config.OPENAI_MODEL = original_model
            config.OPENAI_REASONING_EFFORT = original_effort

    return BenchmarkResult(
        model=model,
        reasoning_effort=reasoning_effort,
        elapsed_seconds=elapsed,
        scores=scores,
        usage=usage,
    )


def print_dataset_summary(articles: list[Article]) -> None:
    source_counts = Counter(article.source for article in articles)
    print("=" * 72)
    print("Benchmark dataset")
    print("=" * 72)
    print(f"Articles: {len(articles)}")
    print("Sources:")
    for source, count in source_counts.items():
        print(f"  - {source}: {count}")
    print()


def print_result(label: str, result: BenchmarkResult) -> None:
    print("=" * 72)
    print(label)
    print("=" * 72)
    print(f"Model: {result.model}")
    print(f"Reasoning effort: {result.reasoning_effort or 'disabled'}")
    print(f"Elapsed: {result.elapsed_seconds:.2f}s")
    print(f"API calls: {result.usage.api_calls}")
    print(f"Input tokens: {result.usage.input_tokens}")
    print(f"Output tokens: {result.usage.output_tokens}")
    print(f"Reasoning tokens: {result.usage.reasoning_tokens}")
    print(f"Estimated cost: ${result.estimated_cost_usd:.6f}")
    print(f"Fallback rate: {fallback_rate(result.scores):.1%}")
    print(f"Summary-in-range rate: {summary_in_target_rate(result.scores):.1%}")
    print()


def print_comparison(
    baseline: BenchmarkResult, candidate: BenchmarkResult, cost_ceiling: float
) -> None:
    baseline_cost = baseline.estimated_cost_usd
    candidate_cost = candidate.estimated_cost_usd
    cost_multiplier = (
        candidate_cost / baseline_cost if baseline_cost > 0 else float("inf")
    )
    latency_multiplier = (
        candidate.elapsed_seconds / baseline.elapsed_seconds
        if baseline.elapsed_seconds > 0
        else float("inf")
    )

    print("=" * 72)
    print("Comparison")
    print("=" * 72)
    print(f"Cost multiplier: {cost_multiplier:.2f}x (ceiling {cost_ceiling:.2f}x)")
    print(f"Latency multiplier: {latency_multiplier:.2f}x")
    print(
        f"Fallback delta: {fallback_rate(candidate.scores) - fallback_rate(baseline.scores):+.1%}"
    )
    print(
        "Summary-in-range delta: "
        f"{summary_in_target_rate(candidate.scores) - summary_in_target_rate(baseline.scores):+.1%}"
    )
    print(
        f"Total-score correlation: {pearson_total_correlation(baseline.scores, candidate.scores):.3f}"
    )
    print(
        f"Mean absolute total gap: {mean_absolute_total_gap(baseline.scores, candidate.scores):.2f}"
    )
    print()


async def async_main(args: argparse.Namespace) -> int:
    if not config.OPENAI_API_KEY:
        print("OPENAI_API_KEY is not set; cannot run live benchmark.")
        return 1

    articles = await load_articles(args.article_limit)
    if not articles:
        print("No benchmark articles were fetched.")
        return 1

    print_dataset_summary(articles)

    baseline_effort = (
        args.baseline_effort
        if args.baseline_effort is not None
        else config.default_openai_reasoning_effort(args.baseline_model)
    )
    candidate_effort = (
        args.candidate_effort
        if args.candidate_effort is not None
        else config.default_openai_reasoning_effort(args.candidate_model)
    )

    baseline = await run_model(
        articles, model=args.baseline_model, reasoning_effort=baseline_effort
    )
    candidate = await run_model(
        articles, model=args.candidate_model, reasoning_effort=candidate_effort
    )

    print_result("Baseline", baseline)
    print_result("Candidate", candidate)
    print_comparison(baseline, candidate, args.cost_ceiling)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark gpt-5-nano and GPT-5.4 candidates on live RSS articles."
    )
    parser.add_argument("--baseline-model", default="gpt-5-nano")
    parser.add_argument("--candidate-model", default="gpt-5.4-nano")
    parser.add_argument("--baseline-effort")
    parser.add_argument("--candidate-effort")
    parser.add_argument("--article-limit", type=int, default=24)
    parser.add_argument("--cost-ceiling", type=float, default=3.5)
    return parser.parse_args()


def main() -> int:
    return asyncio.run(async_main(parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
