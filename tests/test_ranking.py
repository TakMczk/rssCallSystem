import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timezone, timedelta
from src import config
from src.models import Article, ScoreResult, RankedArticle
from src.ranking import sort_ranked


FIXED_NOW = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)


def configure_ranking(
    monkeypatch,
    *,
    enable_diversity=True,
    freshness_half_life_hours=18.0,
    freshness_max_bonus=6.0,
    source_repeat_penalty=3.0,
):
    monkeypatch.setattr(config, "RANKING_ENABLE_HYBRID", True, raising=False)
    monkeypatch.setattr(config, "RANKING_ENABLE_DIVERSITY", enable_diversity, raising=False)
    monkeypatch.setattr(
        config,
        "RANKING_FRESHNESS_HALF_LIFE_HOURS",
        freshness_half_life_hours,
        raising=False,
    )
    monkeypatch.setattr(
        config,
        "RANKING_FRESHNESS_MAX_BONUS",
        freshness_max_bonus,
        raising=False,
    )
    monkeypatch.setattr(
        config,
        "RANKING_SOURCE_REPEAT_PENALTY",
        source_repeat_penalty,
        raising=False,
    )


def make_article(
    *,
    novelty,
    expertise,
    interest,
    idx,
    source="x",
    published_at=None,
    url=None,
    cultural_relevance=5,
    lifestyle_connection=5,
    creativity=5,
):
    a = Article(
        id=str(idx),
        source=source,
        title=f"t{idx}",
        url=url or f"https://{source}.example.com/{idx}",
        published_at=published_at or (FIXED_NOW - timedelta(minutes=idx)),
        summary="s",
        excerpt="e",
    )
    score = ScoreResult(
        novelty=novelty, interest=interest, expertise=expertise,
        cultural_relevance=cultural_relevance, lifestyle_connection=lifestyle_connection, creativity=creativity,
        reason="r"
    )
    return RankedArticle(**a.model_dump(), scores=score)


def test_sort_ranked_preserves_score_priority_when_articles_are_otherwise_equal(monkeypatch):
    configure_ranking(monkeypatch, enable_diversity=False)
    published_at = FIXED_NOW - timedelta(hours=2)
    arts = [
        make_article(
            novelty=7,
            expertise=7,
            interest=7,
            idx=1,
            source="alpha",
            published_at=published_at,
        ),
        make_article(
            novelty=5,
            expertise=5,
            interest=5,
            idx=2,
            source="alpha",
            published_at=published_at,
        ),
    ]

    sorted_ = sort_ranked(arts, now=FIXED_NOW)

    assert sorted_[0].id == "1"
    assert sorted_[1].id == "2"


def test_sort_ranked_applies_freshness_bonus_for_close_scores(monkeypatch):
    configure_ranking(monkeypatch, enable_diversity=False)
    arts = [
        make_article(
            novelty=7,
            expertise=7,
            interest=7,
            idx=1,
            source="alpha",
            published_at=FIXED_NOW - timedelta(hours=30),
        ),
        make_article(
            novelty=7,
            expertise=6,
            interest=7,
            idx=2,
            source="beta",
            published_at=FIXED_NOW - timedelta(hours=1),
        ),
    ]

    sorted_ = sort_ranked(arts, now=FIXED_NOW)

    assert sorted_[0].id == "2"


def test_sort_ranked_applies_soft_source_diversity_penalty(monkeypatch):
    configure_ranking(monkeypatch, enable_diversity=True, source_repeat_penalty=3.0)
    published_at = FIXED_NOW - timedelta(hours=2)
    arts = [
        make_article(
            novelty=8,
            expertise=7,
            interest=7,
            idx=1,
            source="alpha",
            published_at=published_at,
        ),
        make_article(
            novelty=7,
            expertise=7,
            interest=7,
            idx=2,
            source="alpha",
            published_at=published_at,
        ),
        make_article(
            novelty=7,
            expertise=7,
            interest=7,
            idx=3,
            source="beta",
            published_at=published_at,
        ),
    ]

    sorted_ = sort_ranked(arts, now=FIXED_NOW)

    assert [article.id for article in sorted_[:3]] == ["1", "3", "2"]


def test_sort_ranked_does_not_let_freshness_override_large_score_gap(monkeypatch):
    configure_ranking(monkeypatch, enable_diversity=False)
    arts = [
        make_article(
            novelty=10,
            expertise=10,
            interest=10,
            idx=1,
            source="alpha",
            published_at=FIXED_NOW - timedelta(hours=18),
        ),
        make_article(
            novelty=5,
            expertise=5,
            interest=5,
            idx=2,
            source="beta",
            published_at=FIXED_NOW - timedelta(minutes=10),
        ),
    ]

    sorted_ = sort_ranked(arts, now=FIXED_NOW)

    assert sorted_[0].id == "1"


def test_sort_ranked_does_not_use_future_freshness_as_tie_breaker(monkeypatch):
    configure_ranking(monkeypatch, enable_diversity=False)
    base_published_at = FIXED_NOW - timedelta(hours=2)
    first = make_article(
        novelty=7,
        expertise=7,
        interest=7,
        idx=2,
        source="alpha",
        published_at=base_published_at,
    ).model_copy(update={"freshness_at": FIXED_NOW})
    second = make_article(
        novelty=7,
        expertise=7,
        interest=7,
        idx=1,
        source="beta",
        published_at=base_published_at,
    ).model_copy(update={"freshness_at": FIXED_NOW + timedelta(days=30)})

    sorted_ = sort_ranked([first, second], now=FIXED_NOW)

    assert [article.id for article in sorted_] == ["2", "1"]


def test_sort_ranked_uses_article_domain_for_diversity_not_feed_url(monkeypatch):
    configure_ranking(monkeypatch, enable_diversity=True, source_repeat_penalty=3.0)
    published_at = FIXED_NOW - timedelta(hours=2)
    hatena_feed = "https://b.hatena.ne.jp/hotentry/it.rss"
    arts = [
        make_article(
            novelty=8,
            expertise=7,
            interest=7,
            idx=1,
            source=hatena_feed,
            url="https://publisher-a.example.com/story-1",
            published_at=published_at,
        ),
        make_article(
            novelty=7,
            expertise=7,
            interest=7,
            idx=2,
            source=hatena_feed,
            url="https://publisher-b.example.com/story-2",
            published_at=published_at,
        ),
        make_article(
            novelty=7,
            expertise=7,
            interest=7,
            idx=3,
            source="https://xenospectrum.com/feed/",
            url="https://publisher-c.example.com/story-3",
            published_at=published_at,
            cultural_relevance=4,
        ),
    ]

    sorted_ = sort_ranked(arts, now=FIXED_NOW)

    assert [article.id for article in sorted_[:3]] == ["1", "2", "3"]


def test_sort_ranked_handles_malformed_urls_by_falling_back_to_source(monkeypatch):
    configure_ranking(monkeypatch, enable_diversity=True, source_repeat_penalty=3.0)
    published_at = FIXED_NOW - timedelta(hours=2)
    arts = [
        make_article(
            novelty=8,
            expertise=7,
            interest=7,
            idx=1,
            source="https://alpha.example/feed/",
            url="https://[broken-url/story-1",
            published_at=published_at,
        ),
        make_article(
            novelty=7,
            expertise=7,
            interest=7,
            idx=2,
            source="https://alpha.example/feed/",
            url="https://[broken-url/story-2",
            published_at=published_at,
        ),
        make_article(
            novelty=7,
            expertise=7,
            interest=7,
            idx=3,
            source="https://beta.example/feed/",
            url="https://publisher-b.example/story-3",
            published_at=published_at,
        ),
    ]

    sorted_ = sort_ranked(arts, now=FIXED_NOW)

    assert [article.id for article in sorted_[:3]] == ["1", "3", "2"]


def test_sort_ranked_normalizes_source_host_when_falling_back(monkeypatch):
    configure_ranking(monkeypatch, enable_diversity=True, source_repeat_penalty=3.0)
    published_at = FIXED_NOW - timedelta(hours=2)
    arts = [
        make_article(
            novelty=8,
            expertise=7,
            interest=7,
            idx=1,
            source="https://www.alpha.example/feed/",
            url="/relative-story-1",
            published_at=published_at,
        ),
        make_article(
            novelty=7,
            expertise=7,
            interest=7,
            idx=2,
            source="https://alpha.example/rss",
            url="/relative-story-2",
            published_at=published_at,
        ),
        make_article(
            novelty=7,
            expertise=7,
            interest=7,
            idx=3,
            source="https://beta.example/feed/",
            url="/relative-story-3",
            published_at=published_at,
        ),
    ]

    sorted_ = sort_ranked(arts, now=FIXED_NOW)

    assert [article.id for article in sorted_[:3]] == ["1", "3", "2"]


def test_sort_ranked_uses_tenant_aware_diversity_key_for_platform_hosts(monkeypatch):
    configure_ranking(monkeypatch, enable_diversity=True, source_repeat_penalty=3.0)
    published_at = FIXED_NOW - timedelta(hours=2)
    arts = [
        make_article(
            novelty=8,
            expertise=7,
            interest=7,
            idx=1,
            source="https://zenn.dev/feed",
            url="https://zenn.dev/alice/articles/story-1",
            published_at=published_at,
        ),
        make_article(
            novelty=7,
            expertise=7,
            interest=7,
            idx=2,
            source="https://zenn.dev/feed",
            url="https://zenn.dev/bob/articles/story-2",
            published_at=published_at,
        ),
        make_article(
            novelty=7,
            expertise=7,
            interest=7,
            idx=3,
            source="https://xenospectrum.com/feed/",
            url="https://publisher-c.example.com/story-3",
            published_at=published_at,
            cultural_relevance=4,
        ),
    ]

    sorted_ = sort_ranked(arts, now=FIXED_NOW)

    assert [article.id for article in sorted_[:3]] == ["1", "2", "3"]
