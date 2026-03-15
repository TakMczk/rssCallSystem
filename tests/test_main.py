import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.fetcher import _DEF_PUB_DT
from src import config, main
from src.main import filter_recent_articles
from src.models import Article


def make_article(
    article_id: str,
    *,
    published_at: datetime,
    freshness_at: datetime | None = None,
) -> Article:
    return Article(
        id=article_id,
        source="https://publisher.example/feed/",
        title=f"Title {article_id}",
        url=f"https://publisher.example/articles/{article_id}",
        published_at=published_at,
        freshness_at=freshness_at,
        summary="Summary",
        excerpt="Excerpt",
    )


def test_filter_recent_articles_uses_freshness_when_newer():
    now = datetime.now(timezone.utc)
    articles = [
        make_article(
            "old-but-updated",
            published_at=now - timedelta(hours=36),
            freshness_at=now - timedelta(hours=1),
        ),
        make_article(
            "old-and-stale",
            published_at=now - timedelta(hours=36),
            freshness_at=now - timedelta(hours=36),
        ),
    ]

    filtered = filter_recent_articles(articles, hours=24)

    assert [article.id for article in filtered] == ["old-but-updated"]


def test_filter_recent_articles_keeps_updated_only_articles_with_default_publish_date():
    now = datetime.now(timezone.utc)
    articles = [
        make_article(
            "updated-only",
            published_at=_DEF_PUB_DT,
            freshness_at=now - timedelta(hours=1),
        )
    ]

    filtered = filter_recent_articles(articles, hours=24)

    assert [article.id for article in filtered] == ["updated-only"]


def test_filter_recent_articles_rejects_updated_only_articles_with_far_future_freshness():
    now = datetime.now(timezone.utc)
    articles = [
        make_article(
            "future-updated-only",
            published_at=_DEF_PUB_DT,
            freshness_at=now + timedelta(days=30),
        )
    ]

    filtered = filter_recent_articles(articles, hours=24)

    assert filtered == []


def test_filter_recent_articles_does_not_revive_too_old_articles():
    now = datetime.now(timezone.utc)
    articles = [
        make_article(
            "too-old-but-updated",
            published_at=now - timedelta(days=5),
            freshness_at=now - timedelta(hours=1),
        )
    ]

    filtered = filter_recent_articles(articles, hours=24)

    assert filtered == []


def test_run_rewrites_output_with_empty_feed_when_no_recent_articles(
    monkeypatch, tmp_path
):
    output_path = tmp_path / "rss.xml"
    output_path.write_text("stale feed", encoding="utf-8")
    monkeypatch.setattr(config, "OUTPUT_RSS_PATH", str(output_path), raising=False)
    monkeypatch.setattr(
        config, "FEED_URLS", ["https://example.com/feed"], raising=False
    )

    async def fake_fetch_all_feeds(urls):
        return ["raw-item"]

    monkeypatch.setattr(main, "fetch_all_feeds", fake_fetch_all_feeds)
    monkeypatch.setattr(
        main,
        "normalize",
        lambda raw: [
            make_article(
                "too-old",
                published_at=datetime.now(timezone.utc) - timedelta(days=5),
            )
        ],
    )

    asyncio.run(main.run())

    xml = output_path.read_text(encoding="utf-8")
    assert "stale feed" not in xml
    assert "<rss" in xml
    assert "<item>" not in xml


def test_run_preserves_previous_output_when_fetch_and_normalize_produce_no_items(
    monkeypatch, tmp_path
):
    output_path = tmp_path / "rss.xml"
    output_path.write_text("stale feed", encoding="utf-8")
    monkeypatch.setattr(config, "OUTPUT_RSS_PATH", str(output_path), raising=False)
    monkeypatch.setattr(
        config, "FEED_URLS", ["https://example.com/feed"], raising=False
    )

    async def fake_fetch_all_feeds(urls):
        return []

    monkeypatch.setattr(main, "fetch_all_feeds", fake_fetch_all_feeds)
    monkeypatch.setattr(main, "normalize", lambda raw: [])

    asyncio.run(main.run())

    assert output_path.read_text(encoding="utf-8") == "stale feed"
