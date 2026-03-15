import os
import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.fetcher import (
    _canonicalize_url,
    _extract_freshness_datetime,
    _extract_published_datetime,
    normalize,
)
from src.models import RawFeedItem


def make_raw(
    *,
    source: str,
    title: str,
    link: str,
    published: datetime | None,
    updated: datetime | None = None,
    summary: str = "",
    content: str | None = None,
) -> RawFeedItem:
    return RawFeedItem(
        source=source,
        title=title,
        link=link,
        published=published,
        updated=updated,
        summary=summary,
        content=content,
    )


def test_extract_published_datetime_does_not_treat_updated_as_published():
    entry = {"updated": "2026-03-15T09:00:00+09:00"}

    parsed = _extract_published_datetime(entry)

    assert parsed is None


def test_extract_published_datetime_ignores_updated_parsed_when_publish_missing():
    entry = {"updated_parsed": time.strptime("2026-03-15 09:00:00", "%Y-%m-%d %H:%M:%S")}

    parsed = _extract_published_datetime(entry)

    assert parsed is None


def test_extract_freshness_datetime_uses_updated_when_publish_missing():
    entry = {"updated": "2026-03-15T09:00:00+09:00"}

    parsed = _extract_freshness_datetime(entry)

    assert parsed is not None
    assert parsed.astimezone(timezone.utc) == datetime(
        2026, 3, 15, 0, 0, tzinfo=timezone.utc
    )


def test_extract_freshness_datetime_prefers_parsed_tuple_over_naive_string():
    entry = {
        "updated": "2026-03-15 09:00:00",
        "updated_parsed": time.strptime("2026-03-15 00:00:00", "%Y-%m-%d %H:%M:%S"),
    }

    parsed = _extract_freshness_datetime(entry)

    assert parsed is not None
    assert parsed == datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)


def test_normalize_deduplicates_same_story_across_feeds_even_if_metadata_differs():
    published = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
    raw_items = [
        make_raw(
            source="https://example.com/feed/",
            title="Interesting story",
            link="https://example.com/articles/1",
            published=published,
            summary="Direct summary",
        ),
        make_raw(
            source="https://b.hatena.ne.jp/hotentry/it.rss",
            title="[B! 123 users] Interesting story",
            link="https://example.com/articles/1",
            published=published + timedelta(minutes=10),
            summary="Aggregator summary",
        ),
    ]

    articles = normalize(raw_items)

    assert len(articles) == 1


def test_normalize_canonicalizes_tracking_variants_before_deduplication():
    published = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
    raw_items = [
        make_raw(
            source="https://b.hatena.ne.jp/hotentry/it.rss",
            title="Interesting story",
            link="https://example.com/articles/1?utm_source=hatena#bookmark",
            published=published,
            summary="Aggregator summary",
        ),
        make_raw(
            source="https://example.com/feed/",
            title="Interesting story",
            link="https://example.com/articles/1",
            published=published,
            summary="Direct summary",
        ),
    ]

    articles = normalize(raw_items)

    assert len(articles) == 1
    assert str(articles[0].url) == "https://example.com/articles/1"


def test_normalize_deduplicates_www_and_apex_article_urls():
    published = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
    raw_items = [
        make_raw(
            source="https://example.com/feed/",
            title="Interesting story",
            link="https://www.example.com/articles/1",
            published=published,
            summary="Direct summary",
        ),
        make_raw(
            source="https://b.hatena.ne.jp/hotentry/it.rss",
            title="[B! 123 users] Interesting story",
            link="https://example.com/articles/1",
            published=published + timedelta(minutes=10),
            summary="Aggregator summary",
        ),
    ]

    articles = normalize(raw_items)

    assert len(articles) == 1
    assert str(articles[0].url) == "https://www.example.com/articles/1"


def test_canonicalize_url_preserves_invalid_port_without_crashing():
    assert (
        _canonicalize_url("https://example.com:bad/articles/1")
        == "https://example.com:bad/articles/1"
    )


def test_canonicalize_url_preserves_userinfo_without_rewriting():
    assert (
        _canonicalize_url("https://user:pass@example.com/private?utm_source=hatena")
        == "https://user:pass@example.com/private?utm_source=hatena"
    )


def test_canonicalize_url_preserves_ipv6_brackets():
    assert (
        _canonicalize_url("https://[2001:db8::1]/articles/1?utm_source=hatena")
        == "https://[2001:db8::1]/articles/1"
    )


def test_canonicalize_url_sorts_remaining_query_parameters():
    assert (
        _canonicalize_url("https://example.com/articles/1?b=2&a=1&utm_source=hatena")
        == "https://example.com/articles/1?a=1&b=2"
    )


def test_canonicalize_url_preserves_malformed_bracketed_url_without_crashing():
    assert (
        _canonicalize_url("https://[2001:db8::1/articles/1")
        == "https://[2001:db8::1/articles/1"
    )


def test_normalize_does_not_deduplicate_relative_links_across_feeds():
    published = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
    raw_items = [
        make_raw(
            source="https://feed-a.example/rss.xml",
            title="Story A",
            link="/articles/1",
            published=published,
            summary="Source A summary",
        ),
        make_raw(
            source="https://feed-b.example/rss.xml",
            title="Story B",
            link="/articles/1",
            published=published,
            summary="Source B summary",
        ),
    ]

    articles = normalize(raw_items)

    assert len(articles) == 2


def test_normalize_resolves_relative_links_against_feed_url():
    published = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
    raw_items = [
        make_raw(
            source="https://publisher.example/feed/",
            title="Relative story",
            link="/articles/1",
            published=published,
            summary="Summary",
        )
    ]

    articles = normalize(raw_items)

    assert len(articles) == 1
    assert str(articles[0].url) == "https://publisher.example/articles/1"


def test_normalize_preserves_malformed_absolute_like_links_without_crashing():
    published = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
    raw_items = [
        make_raw(
            source="https://publisher.example/feed/",
            title="Broken link story",
            link="https://[broken-url/story-1",
            published=published,
            summary="Summary",
        )
    ]

    articles = normalize(raw_items)

    assert len(articles) == 1
    assert str(articles[0].url) == "https://[broken-url/story-1"


def test_normalize_preserves_original_permalink_for_output():
    published = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
    raw_items = [
        make_raw(
            source="https://feed.example/rss.xml",
            title="Tracked story",
            link="https://www.example.com/articles/1?b=2&a=1&utm_source=hatena#frag",
            published=published,
            summary="Summary",
        )
    ]

    articles = normalize(raw_items)

    assert len(articles) == 1
    assert (
        str(articles[0].url)
        == "https://www.example.com/articles/1?b=2&a=1&utm_source=hatena#frag"
    )


def test_normalize_keeps_distinct_titles_for_same_absolute_permalink():
    published = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
    raw_items = [
        make_raw(
            source="https://feed-a.example/rss.xml",
            title="Morning edition",
            link="https://example.com/live",
            published=published,
            summary="Morning summary",
        ),
        make_raw(
            source="https://feed-a.example/rss.xml",
            title="Evening edition",
            link="https://example.com/live",
            published=published + timedelta(hours=8),
            summary="Evening summary",
        ),
    ]

    articles = normalize(raw_items)

    assert len(articles) == 2


def test_normalize_assigns_order_independent_ids_for_distinct_items_sharing_permalink():
    published = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
    raw_items = [
        make_raw(
            source="https://feed-a.example/rss.xml",
            title="Morning edition",
            link="https://example.com/live",
            published=published,
            summary="Morning summary",
        ),
        make_raw(
            source="https://feed-a.example/rss.xml",
            title="Evening edition",
            link="https://example.com/live",
            published=published + timedelta(hours=8),
            summary="Evening summary",
        ),
    ]

    forward = {
        (article.title, article.published_at): article.id
        for article in normalize(raw_items)
    }
    reverse = {
        (article.title, article.published_at): article.id
        for article in normalize(list(reversed(raw_items)))
    }

    assert len(forward) == 2
    assert len(set(forward.values())) == 2
    assert forward == reverse


def test_normalize_keeps_same_title_updates_when_permalink_is_reused_far_apart():
    published = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
    raw_items = [
        make_raw(
            source="https://example.com/feed/",
            title="Daily briefing",
            link="https://example.com/live",
            published=published,
            summary="Morning summary",
        ),
        make_raw(
            source="https://example.com/feed/",
            title="Daily briefing",
            link="https://example.com/live",
            published=published + timedelta(days=2),
            summary="Later summary",
        ),
    ]

    articles = normalize(raw_items)

    assert len(articles) == 2


def test_normalize_keeps_same_title_updates_within_window_when_content_changes():
    published = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
    raw_items = [
        make_raw(
            source="https://example.com/feed/",
            title="Daily briefing",
            link="https://example.com/live",
            published=published,
            summary="Morning update about market open",
            content="Morning edition content with opening details.",
        ),
        make_raw(
            source="https://example.com/feed/",
            title="Daily briefing",
            link="https://example.com/live",
            published=published + timedelta(hours=6),
            summary="Evening update about market close",
            content="Evening edition content with closing details.",
        ),
    ]

    articles = normalize(raw_items)

    assert len(articles) == 2


def test_normalize_keeps_cross_feed_same_title_updates_within_window_when_content_changes():
    published = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
    raw_items = [
        make_raw(
            source="https://b.hatena.ne.jp/hotentry/it.rss",
            title="[B! 123 users] Daily briefing",
            link="https://example.com/live",
            published=published,
            summary="Morning update about market open",
            content="Morning edition content with opening details and first figures.",
        ),
        make_raw(
            source="https://example.com/feed/",
            title="Daily briefing",
            link="https://example.com/live",
            published=published + timedelta(hours=6),
            summary="Evening update about market close",
            content="Evening edition content with closing details and final figures.",
        ),
    ]

    articles = normalize(raw_items)

    assert len(articles) == 2


def test_normalize_keeps_cross_feed_same_title_updates_when_permalink_is_reused_far_apart():
    published = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
    raw_items = [
        make_raw(
            source="https://b.hatena.ne.jp/hotentry/it.rss",
            title="[B! 123 users] Daily briefing",
            link="https://example.com/live",
            published=published,
            summary="Aggregator summary",
        ),
        make_raw(
            source="https://example.com/feed/",
            title="Daily briefing",
            link="https://example.com/live",
            published=published + timedelta(days=2),
            summary="Updated publisher summary",
        ),
    ]

    articles = normalize(raw_items)

    assert len(articles) == 2


def test_normalize_merges_same_canonical_url_far_apart_when_content_matches():
    published = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
    raw_items = [
        make_raw(
            source="https://b.hatena.ne.jp/hotentry/it.rss",
            title="[B! 123 users] Interesting story",
            link="https://example.com/articles/1",
            published=published,
            summary="Shared summary text describing the same story in enough detail.",
            content="Shared excerpt text describing the same story in enough detail.",
        ),
        make_raw(
            source="https://example.com/feed/",
            title="Interesting story",
            link="https://example.com/articles/1",
            published=published + timedelta(days=2),
            summary="Shared summary text describing the same story in enough detail.",
            content="Shared excerpt text describing the same story in enough detail.",
        ),
    ]

    articles = normalize(raw_items)

    assert len(articles) == 1


def test_normalize_keeps_same_title_updates_when_one_publish_timestamp_is_missing():
    published = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
    raw_items = [
        make_raw(
            source="https://example.com/feed/",
            title="Daily briefing",
            link="https://example.com/live",
            published=None,
            summary="Undated summary",
        ),
        make_raw(
            source="https://example.com/feed/",
            title="Daily briefing",
            link="https://example.com/live",
            published=published + timedelta(days=2),
            summary="Dated summary",
        ),
    ]

    articles = normalize(raw_items)

    assert len(articles) == 2


def test_normalize_preserves_clean_title_and_earliest_publish_time_when_merging():
    direct_published = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
    raw_items = [
        make_raw(
            source="https://b.hatena.ne.jp/hotentry/it.rss",
            title="[B! 123 users] Interesting story",
            link="https://example.com/articles/1",
            published=direct_published + timedelta(hours=6),
            summary="A much longer aggregator summary that should not overwrite metadata.",
        ),
        make_raw(
            source="https://example.com/feed/",
            title="Interesting story",
            link="https://example.com/articles/1",
            published=direct_published,
            summary="Direct summary",
        ),
    ]

    articles = normalize(raw_items)

    assert len(articles) == 1
    assert articles[0].title == "Interesting story"
    assert articles[0].published_at == direct_published
    assert articles[0].freshness_at == direct_published
    assert articles[0].summary == "Direct summary"


def test_normalize_uses_updated_time_for_freshness_when_present():
    published = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
    updated = published + timedelta(hours=6)
    raw_items = [
        make_raw(
            source="https://publisher.example/feed/",
            title="Updated story",
            link="https://publisher.example/articles/1",
            published=published,
            updated=updated,
            summary="Publisher summary",
        )
    ]

    articles = normalize(raw_items)

    assert len(articles) == 1
    assert articles[0].published_at == published
    assert articles[0].freshness_at == updated


def test_normalize_prefers_same_host_metadata_over_richer_cross_host_feed():
    published = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
    raw_items = [
        make_raw(
            source="https://curator.example/feed/",
            title="[B! 42 users] Publisher story",
            link="https://publisher.example/articles/1",
            published=published + timedelta(minutes=5),
            summary="Curator summary with much richer text that should not override the publisher.",
            content="Curator excerpt that should not replace trusted publisher metadata.",
        ),
        make_raw(
            source="https://publisher.example/feed/",
            title="Publisher story",
            link="https://publisher.example/articles/1",
            published=published,
            summary="Publisher summary",
            content="Publisher excerpt",
        ),
    ]

    articles = normalize(raw_items)

    assert len(articles) == 1
    assert articles[0].source == "https://publisher.example/feed/"
    assert articles[0].title == "Publisher story"
    assert articles[0].summary == "Publisher summary"
    assert articles[0].excerpt == "Publisher excerpt"
    assert str(articles[0].url) == "https://publisher.example/articles/1"


def test_normalize_treats_www_feed_host_as_trusted_publisher():
    published = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
    raw_items = [
        make_raw(
            source="https://curator.example/feed/",
            title="[B! 42 users] Publisher story",
            link="https://publisher.example/articles/1",
            published=published + timedelta(minutes=5),
            summary="Curator summary with more text than the original publisher.",
        ),
        make_raw(
            source="https://www.publisher.example/feed/",
            title="Publisher story",
            link="https://publisher.example/articles/1",
            published=published,
            summary="Publisher summary",
        ),
    ]

    articles = normalize(raw_items)

    assert len(articles) == 1
    assert articles[0].source == "https://www.publisher.example/feed/"
    assert articles[0].title == "Publisher story"
    assert articles[0].summary == "Publisher summary"


def test_normalize_treats_feed_subdomain_as_trusted_publisher():
    published = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
    raw_items = [
        make_raw(
            source="https://b.hatena.ne.jp/hotentry/it.rss",
            title="[B! 200 users] ZDNet story",
            link="https://japan.zdnet.com/article/35123456/",
            published=published + timedelta(minutes=10),
            summary="Hatena summary with more text than the original feed.",
        ),
        make_raw(
            source="https://feeds.japan.zdnet.com/rss/zdnet/all.rdf",
            title="ZDNet story",
            link="https://japan.zdnet.com/article/35123456/",
            published=published,
            summary="ZDNet summary",
        ),
    ]

    articles = normalize(raw_items)

    assert len(articles) == 1
    assert articles[0].source == "https://feeds.japan.zdnet.com/rss/zdnet/all.rdf"
    assert articles[0].title == "ZDNet story"
    assert articles[0].summary == "ZDNet summary"


def test_normalize_does_not_treat_hatena_wrapper_url_as_trusted_freshness():
    updated = datetime(2026, 3, 15, 6, 0, tzinfo=timezone.utc)
    raw_items = [
        make_raw(
            source="https://b.hatena.ne.jp/hotentry/it.rss",
            title="[B! 123 users] Wrapped story",
            link="https://b.hatena.ne.jp/entry/s/example.com/articles/1",
            published=None,
            updated=updated,
            summary="Hatena wrapper summary",
        )
    ]

    articles = normalize(raw_items)

    assert len(articles) == 1
    assert articles[0].published_at == datetime(1970, 1, 1, tzinfo=timezone.utc)
    assert articles[0].freshness_at == datetime(1970, 1, 1, tzinfo=timezone.utc)
