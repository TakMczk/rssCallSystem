from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import sqrt
from typing import Sequence

from .models import Article, ScoreResult


@dataclass(frozen=True)
class ModelPricing:
    input_per_million: float
    output_per_million: float


MODEL_PRICING: dict[str, ModelPricing] = {
    "gpt-5-nano": ModelPricing(input_per_million=0.05, output_per_million=0.40),
    "gpt-5.4-nano": ModelPricing(input_per_million=0.20, output_per_million=1.25),
    "gpt-5.4-mini": ModelPricing(input_per_million=0.75, output_per_million=4.50),
    "gpt-5.4": ModelPricing(input_per_million=2.50, output_per_million=15.00),
}


def select_representative_articles(
    articles: Sequence[Article], limit: int
) -> list[Article]:
    if limit <= 0:
        return []

    grouped: dict[str, deque[Article]] = {}
    source_order: list[str] = []
    for article in articles:
        if article.source not in grouped:
            grouped[article.source] = deque()
            source_order.append(article.source)
        grouped[article.source].append(article)

    selected: list[Article] = []
    while len(selected) < limit:
        progressed = False
        for source in source_order:
            queue = grouped[source]
            if not queue:
                continue
            selected.append(queue.popleft())
            progressed = True
            if len(selected) >= limit:
                break
        if not progressed:
            break
    return selected


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = MODEL_PRICING[model]
    return (
        (input_tokens / 1_000_000) * pricing.input_per_million
        + (output_tokens / 1_000_000) * pricing.output_per_million
    )


def fallback_rate(scores: Sequence[ScoreResult]) -> float:
    if not scores:
        return 0.0
    fallback_count = sum(score.reason.startswith("fallback:") for score in scores)
    return fallback_count / len(scores)


def summary_in_target_rate(
    scores: Sequence[ScoreResult], minimum: int = 160, maximum: int = 240
) -> float:
    if not scores:
        return 0.0

    in_range = 0
    for score in scores:
        summary = score.summary_ja or ""
        if minimum <= len(summary) <= maximum:
            in_range += 1
    return in_range / len(scores)


def mean_absolute_total_gap(
    baseline: Sequence[ScoreResult], candidate: Sequence[ScoreResult]
) -> float:
    count = min(len(baseline), len(candidate))
    if count == 0:
        return 0.0
    total_gap = sum(
        abs(left.total - right.total)
        for left, right in zip(baseline[:count], candidate[:count])
    )
    return total_gap / count


def pearson_total_correlation(
    baseline: Sequence[ScoreResult], candidate: Sequence[ScoreResult]
) -> float:
    count = min(len(baseline), len(candidate))
    if count == 0:
        return 0.0

    left = [score.total for score in baseline[:count]]
    right = [score.total for score in candidate[:count]]

    mean_left = sum(left) / count
    mean_right = sum(right) / count
    covariance = sum(
        (left_value - mean_left) * (right_value - mean_right)
        for left_value, right_value in zip(left, right)
    )
    variance_left = sum((value - mean_left) ** 2 for value in left)
    variance_right = sum((value - mean_right) ** 2 for value in right)
    if variance_left == 0 or variance_right == 0:
        return 1.0 if left == right else 0.0
    return covariance / sqrt(variance_left * variance_right)
