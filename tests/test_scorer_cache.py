import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src import config, scorer
from src.models import Article, ScoreResult


def make_article(
    article_id: str,
    *,
    title: str = "Cache test article",
    url: str = "https://example.com/cache-test",
    summary: str = "Summary",
    excerpt: str = "Excerpt",
) -> Article:
    return Article(
        id=article_id,
        source="source",
        title=title,
        url=url,
        published_at=datetime.now(timezone.utc),
        summary=summary,
        excerpt=excerpt,
    )


def make_score(reason: str, summary_ja: str = "要約") -> ScoreResult:
    return ScoreResult(
        novelty=6,
        interest=6,
        expertise=6,
        cultural_relevance=5,
        lifestyle_connection=5,
        creativity=5,
        reason=reason,
        summary_ja=summary_ja,
    )


def reset_cache(monkeypatch, cache_file: Path):
    monkeypatch.setattr(scorer, "CACHE_FILE", cache_file)
    scorer._cache.clear()


def test_score_article_ignores_cache_when_version_changes(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "OPENAI_API_KEY", None)
    article = make_article("a1")
    cache_file = tmp_path / "scores.jsonl"
    reset_cache(monkeypatch, cache_file)

    monkeypatch.setattr(config, "SCORER_CACHE_VERSION", "v1", raising=False)
    monkeypatch.setattr(
        scorer,
        "_generate_heuristic_score",
        lambda article: make_score("cached:v1"),
    )
    first = asyncio.run(scorer.score_article(article))
    assert first.reason == "cached:v1"

    monkeypatch.setattr(config, "SCORER_CACHE_VERSION", "v2", raising=False)
    monkeypatch.setattr(
        scorer,
        "_generate_heuristic_score",
        lambda article: make_score("cached:v2"),
    )
    second = asyncio.run(scorer.score_article(article))

    assert second.reason == "cached:v2"


def test_score_article_reuses_cache_when_version_matches(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "OPENAI_API_KEY", None)
    monkeypatch.setattr(config, "SCORER_CACHE_VERSION", "v1", raising=False)
    article = make_article("a2")
    cache_file = tmp_path / "scores.jsonl"
    reset_cache(monkeypatch, cache_file)

    monkeypatch.setattr(
        scorer,
        "_generate_heuristic_score",
        lambda article: make_score("cached:v1"),
    )
    first = asyncio.run(scorer.score_article(article))
    assert first.reason == "cached:v1"

    monkeypatch.setattr(
        scorer,
        "_generate_heuristic_score",
        lambda article: make_score("cached:v2"),
    )
    second = asyncio.run(scorer.score_article(article))

    assert second.reason == "cached:v1"
    assert second.summary_ja == "要約"


def test_score_articles_reuses_cached_results_in_batch_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "USE_BATCH_SCORING", True)
    monkeypatch.setattr(config, "SCORER_CACHE_VERSION", "v1", raising=False)
    cache_file = tmp_path / "scores.jsonl"
    reset_cache(monkeypatch, cache_file)
    articles = [make_article(f"batch-{index}") for index in range(6)]

    for article in articles:
        scorer._cache[scorer._cache_key(article)] = make_score("cached:batch")

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("batch scorer should not be called for cached articles")

    monkeypatch.setattr(scorer, "score_articles_openai_batch", fail_if_called)

    results = asyncio.run(scorer.score_articles(articles))

    assert len(results) == 6
    assert all(result.reason == "cached:batch" for result in results)


def test_score_article_reuses_cache_across_title_changes_when_url_matches(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(config, "OPENAI_API_KEY", None)
    monkeypatch.setattr(config, "SCORER_CACHE_VERSION", "v1", raising=False)
    cache_file = tmp_path / "scores.jsonl"
    reset_cache(monkeypatch, cache_file)
    first_article = make_article(
        "a-title-1",
        title="[B! 123 users] Story",
        url="https://example.com/shared-story",
    )
    second_article = make_article(
        "a-title-2",
        title="Story",
        url="https://example.com/shared-story",
    )

    monkeypatch.setattr(
        scorer,
        "_generate_heuristic_score",
        lambda article: make_score("cached:title-variant-1"),
    )
    first = asyncio.run(scorer.score_article(first_article))
    assert first.reason == "cached:title-variant-1"

    monkeypatch.setattr(
        scorer,
        "_generate_heuristic_score",
        lambda article: make_score("cached:title-variant-2"),
    )
    second = asyncio.run(scorer.score_article(second_article))

    assert second.reason == "cached:title-variant-1"
    assert second.summary_ja == "要約"


def test_score_article_invalidates_cache_when_model_changes(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "OPENAI_API_KEY", None)
    monkeypatch.setattr(config, "SCORER_CACHE_VERSION", "v1", raising=False)
    monkeypatch.setattr(config, "OPENAI_REASONING_EFFORT", "minimal", raising=False)
    cache_file = tmp_path / "scores.jsonl"
    reset_cache(monkeypatch, cache_file)
    article = make_article("a-model")

    monkeypatch.setattr(config, "OPENAI_MODEL", "gpt-5-nano", raising=False)
    monkeypatch.setattr(
        scorer,
        "_generate_heuristic_score",
        lambda article: make_score("cached:model-gpt5"),
    )
    first = asyncio.run(scorer.score_article(article))
    assert first.reason == "cached:model-gpt5"

    monkeypatch.setattr(config, "OPENAI_MODEL", "gpt-5.4-nano", raising=False)
    monkeypatch.setattr(config, "OPENAI_REASONING_EFFORT", "none", raising=False)
    monkeypatch.setattr(
        scorer,
        "_generate_heuristic_score",
        lambda article: make_score("cached:model-gpt54"),
    )
    second = asyncio.run(scorer.score_article(article))

    assert second.reason == "cached:model-gpt54"


def test_score_article_invalidates_cache_when_reasoning_effort_changes(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(config, "OPENAI_API_KEY", None)
    monkeypatch.setattr(config, "SCORER_CACHE_VERSION", "v1", raising=False)
    monkeypatch.setattr(config, "OPENAI_MODEL", "gpt-5.4-nano", raising=False)
    cache_file = tmp_path / "scores.jsonl"
    reset_cache(monkeypatch, cache_file)
    article = make_article("a-effort")

    monkeypatch.setattr(config, "OPENAI_REASONING_EFFORT", "none", raising=False)
    monkeypatch.setattr(
        scorer,
        "_generate_heuristic_score",
        lambda article: make_score("cached:effort-none"),
    )
    first = asyncio.run(scorer.score_article(article))
    assert first.reason == "cached:effort-none"

    monkeypatch.setattr(config, "OPENAI_REASONING_EFFORT", "low", raising=False)
    monkeypatch.setattr(
        scorer,
        "_generate_heuristic_score",
        lambda article: make_score("cached:effort-low"),
    )
    second = asyncio.run(scorer.score_article(article))

    assert second.reason == "cached:effort-low"


def test_score_article_invalidates_cache_when_content_changes_for_same_url(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(config, "OPENAI_API_KEY", None)
    monkeypatch.setattr(config, "SCORER_CACHE_VERSION", "v1", raising=False)
    cache_file = tmp_path / "scores.jsonl"
    reset_cache(monkeypatch, cache_file)
    first_article = make_article(
        "a-content-1",
        title="Story",
        url="https://example.com/shared-story",
        summary="Original summary",
    )
    second_article = make_article(
        "a-content-2",
        title="Story",
        url="https://example.com/shared-story",
        summary="Updated summary with materially different content",
    )

    monkeypatch.setattr(
        scorer,
        "_generate_heuristic_score",
        lambda article: make_score("cached:content-v1"),
    )
    first = asyncio.run(scorer.score_article(first_article))
    assert first.reason == "cached:content-v1"

    monkeypatch.setattr(
        scorer,
        "_generate_heuristic_score",
        lambda article: make_score("cached:content-v2"),
    )
    second = asyncio.run(scorer.score_article(second_article))

    assert second.reason == "cached:content-v2"


def test_score_article_reuses_fallback_score_in_memory_without_persisting(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(config, "OPENAI_API_KEY", None)
    monkeypatch.setattr(config, "SCORER_CACHE_VERSION", "v1", raising=False)
    cache_file = tmp_path / "scores.jsonl"
    reset_cache(monkeypatch, cache_file)
    article = make_article("fallback-1")
    calls = {"count": 0}

    def generate(article):
        calls["count"] += 1
        return make_score("fallback:no_api")

    monkeypatch.setattr(scorer, "_generate_heuristic_score", generate)

    first = asyncio.run(scorer.score_article(article))
    second = asyncio.run(scorer.score_article(article))

    assert first.reason == "fallback:no_api"
    assert second.reason == "fallback:no_api"
    assert calls["count"] == 1
    assert not cache_file.exists()


def test_score_article_retries_after_transient_fallback_instead_of_reusing_it(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(config, "OPENAI_ORGANIZATION", None)
    monkeypatch.setattr(config, "SCORER_CACHE_VERSION", "v1", raising=False)
    monkeypatch.setattr(config, "MAX_SCORE_RETRY", 1, raising=False)
    cache_file = tmp_path / "scores.jsonl"
    reset_cache(monkeypatch, cache_file)
    article = make_article("retry-1")
    calls = {"count": 0}

    class FakeCompletions:
        async def create(self, **kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("temporary failure")
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content='{"novelty":7,"interest":7,"expertise":7,"cultural_relevance":5,"lifestyle_connection":5,"creativity":5,"reason":"api:ok"}'
                        )
                    )
                ]
            )

    class FakeChat:
        def __init__(self):
            self.completions = FakeCompletions()

    class FakeAsyncOpenAI:
        def __init__(self, *args, **kwargs):
            self.chat = FakeChat()

    monkeypatch.setattr(scorer, "AsyncOpenAI", FakeAsyncOpenAI)

    first = asyncio.run(scorer.score_article(article))
    second = asyncio.run(scorer.score_article(article))

    assert first.reason.startswith("fallback:")
    assert second.reason == "api:ok"
    assert calls["count"] == 2
