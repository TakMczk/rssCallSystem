from __future__ import annotations
import asyncio
import hashlib
import re
from datetime import datetime, timedelta, timezone
from time import struct_time
from typing import Any, List
from urllib.parse import (
    SplitResult,
    parse_qsl,
    urlencode,
    urljoin,
    urlsplit,
    urlunsplit,
)

import feedparser
import httpx
from dateutil import parser as dateparser

from .models import RawFeedItem, Article
from . import config
from .parser_utils import make_excerpt, strip_html
from .logging_utils import get_logger

logger = get_logger(__name__)

USER_AGENT = "TechCuratorBot/0.1 (+https://example.com)"
TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {"fbclid", "gclid", "yclid", "mc_cid", "mc_eid"}
_DEFAULT_PORTS = {"http": 80, "https": 443}
_TRUSTED_HOST_PREFIXES = ("www", "feed", "feeds", "rss")
_UNTRUSTED_FRESHNESS_HOSTS = {"b.hatena.ne.jp"}
_MERGE_PUBLISH_WINDOW_SECONDS = 12 * 60 * 60
_MAX_TRUSTED_FRESHNESS_EXTENSION = timedelta(days=7)


def _get_entry_value(entry: Any, field: str) -> Any:
    if isinstance(entry, dict):
        return entry.get(field)
    return getattr(entry, field, None)


def _ensure_timezone(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _parse_datetime_value(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _ensure_timezone(value)
    if isinstance(value, str):
        try:
            return _ensure_timezone(dateparser.parse(value))
        except (TypeError, ValueError, OverflowError):
            return None
    if isinstance(value, struct_time):
        return datetime(*value[:6], tzinfo=timezone.utc)
    return None


def _extract_published_datetime(entry: Any) -> datetime | None:
    for field in ("published", "created"):
        parsed_struct = _parse_datetime_value(
            _get_entry_value(entry, f"{field}_parsed")
        )
        if parsed_struct is not None:
            return parsed_struct

        parsed = _parse_datetime_value(_get_entry_value(entry, field))
        if parsed is not None:
            return parsed

    return None


def _extract_freshness_datetime(entry: Any) -> datetime | None:
    candidates: list[datetime] = []
    for field in ("published", "updated", "created"):
        parsed_struct = _parse_datetime_value(
            _get_entry_value(entry, f"{field}_parsed")
        )
        if parsed_struct is not None:
            candidates.append(parsed_struct)
            continue

        parsed = _parse_datetime_value(_get_entry_value(entry, field))
        if parsed is not None:
            candidates.append(parsed)

    if not candidates:
        return None
    return max(candidates)


def _safe_urlsplit(value: str) -> SplitResult | None:
    try:
        return urlsplit(value)
    except ValueError:
        return None


def _canonicalize_url(url: str) -> str:
    raw_url = url.strip()
    if not raw_url:
        return raw_url

    split = _safe_urlsplit(raw_url)
    if split is None:
        return raw_url

    if split.username is not None or split.password is not None:
        return raw_url

    if not split.scheme or not split.netloc:
        return raw_url

    filtered_query = sorted(
        [
            (key, value)
            for key, value in parse_qsl(split.query, keep_blank_values=True)
            if key not in TRACKING_QUERY_KEYS
            and not key.startswith(TRACKING_QUERY_PREFIXES)
        ]
    )
    normalized_netloc = _normalized_netloc(split)
    normalized_scheme = split.scheme.lower()
    normalized_path = split.path or "/"
    normalized_query = urlencode(filtered_query, doseq=True)
    return urlunsplit(
        (normalized_scheme, normalized_netloc, normalized_path, normalized_query, "")
    )


def _resolved_link(link: str, source: str) -> str:
    raw_link = link.strip()
    if not raw_link:
        return raw_link

    split = _safe_urlsplit(raw_link)
    if split is not None and split.scheme and split.netloc:
        return raw_link
    if split is not None and split.scheme:
        return raw_link
    try:
        return urljoin(source, raw_link)
    except ValueError:
        return raw_link


def _article_key(link: str, source: str, title: str, published_at: datetime) -> str:
    canonical_url = _canonicalize_url(link)
    canonical_split = _safe_urlsplit(canonical_url)
    if (
        canonical_split is not None
        and canonical_split.scheme
        and canonical_split.netloc
    ):
        return canonical_url
    return f"{source}|{link}|{title}|{int(published_at.timestamp())}"


def _article_richness(summary: str, excerpt: str) -> tuple[int, int]:
    return (len(excerpt.strip()), len(summary.strip()))


def _normalized_title_key(title: str) -> str:
    collapsed = " ".join(title.split())
    normalized = re.sub(r"^\[B![^\]]*\]\s*", "", collapsed, flags=re.IGNORECASE)
    return normalized.lower()


def _titles_look_similar(left_title: str, right_title: str) -> bool:
    left = _normalized_title_key(left_title)
    right = _normalized_title_key(right_title)
    if left == right:
        return True
    shorter, longer = sorted((left, right), key=len)
    return len(shorter) >= 12 and shorter in longer


def _normalized_text_key(text: str) -> str:
    return " ".join(text.split()).lower()


def _text_token_set(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"\w+", _normalized_text_key(text))
        if len(token) >= 4
    }


def _texts_look_similar(left_text: str, right_text: str) -> bool:
    left = _normalized_text_key(left_text)
    right = _normalized_text_key(right_text)
    if not left or not right:
        return False
    if left == right:
        return True
    shorter, longer = sorted((left, right), key=len)
    if len(shorter) >= 40 and shorter in longer:
        return True
    left_tokens = _text_token_set(left)
    right_tokens = _text_token_set(right)
    if not left_tokens or not right_tokens:
        return False
    overlap = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    return union > 0 and (overlap / union) >= 0.75


def _articles_share_duplicate_content(existing: Article, candidate: Article) -> bool:
    text_pairs = [
        (existing.excerpt, candidate.excerpt),
        (existing.summary, candidate.summary),
        (existing.summary, candidate.excerpt),
        (existing.excerpt, candidate.summary),
    ]
    return any(_texts_look_similar(left, right) for left, right in text_pairs)


def _has_rich_article_text(article: Article) -> bool:
    return max(len(article.summary.strip()), len(article.excerpt.strip())) >= 40


def _articles_have_conflicting_rich_content(
    existing: Article, candidate: Article
) -> bool:
    return (
        _has_rich_article_text(existing)
        and _has_rich_article_text(candidate)
        and not _articles_share_duplicate_content(existing, candidate)
    )


def _disambiguated_article_key(article: Article) -> str:
    return (
        f"{article.url}|{article.source}|{_normalized_title_key(article.title)}|"
        f"{int(article.published_at.timestamp())}"
    )


def _normalize_hostname(hostname: str) -> str:
    normalized = hostname.lower().rstrip(".")
    if normalized.startswith("www."):
        return normalized[4:]
    return normalized


def _normalized_netloc(split: SplitResult) -> str:
    try:
        hostname = _normalize_hostname(split.hostname or "")
    except ValueError:
        return split.netloc.lower()
    if not hostname:
        return split.netloc.lower()
    default_port = _DEFAULT_PORTS.get(split.scheme.lower())
    try:
        port = split.port
    except ValueError:
        return split.netloc.lower()

    host_for_netloc = f"[{hostname}]" if ":" in hostname else hostname
    if port and port != default_port:
        return f"{host_for_netloc}:{port}"
    return host_for_netloc


def _host(value: str) -> str:
    split = _safe_urlsplit(value)
    if split is None:
        return ""
    return _normalize_hostname(split.hostname or "")


def _host_variants(host: str) -> set[str]:
    if not host:
        return set()
    variants = {host}
    candidate = host
    while True:
        for prefix in _TRUSTED_HOST_PREFIXES:
            prefix_with_dot = f"{prefix}."
            if candidate.startswith(prefix_with_dot):
                candidate = candidate[len(prefix_with_dot) :]
                variants.add(candidate)
                break
        else:
            return variants


def _is_default_published(value: datetime) -> bool:
    return value == _DEF_PUB_DT


def _looks_like_aggregator_title(title: str) -> bool:
    lowered = title.lower().strip()
    return lowered.startswith("[b!") or "hotentry" in lowered


def _metadata_priority(article: Article) -> tuple[int, int, int, int]:
    excerpt_len, summary_len = _article_richness(article.summary, article.excerpt)
    trusted_host = _is_trusted_article_source(article)
    return (
        1 if trusted_host else 0,
        0 if _looks_like_aggregator_title(article.title) else 1,
        excerpt_len,
        summary_len,
    )


def _is_trusted_article_source(article: Article) -> bool:
    article_host = _host(str(article.url))
    source_host = _host(article.source)
    if source_host in _UNTRUSTED_FRESHNESS_HOSTS:
        return False
    return bool(_host_variants(article_host) & _host_variants(source_host))


def _bounded_trusted_freshness(
    published_at: datetime, freshness_at: datetime
) -> datetime:
    if _is_default_published(published_at):
        return freshness_at
    return max(
        published_at,
        min(freshness_at, published_at + _MAX_TRUSTED_FRESHNESS_EXTENSION),
    )


def _should_merge_articles(existing: Article, candidate: Article) -> bool:
    if not _titles_look_similar(existing.title, candidate.title):
        return False

    if _articles_share_duplicate_content(existing, candidate):
        return True

    if _is_default_published(existing.published_at) or _is_default_published(
        candidate.published_at
    ):
        return False

    publish_delta = abs(
        (existing.published_at - candidate.published_at).total_seconds()
    )
    if publish_delta > _MERGE_PUBLISH_WINDOW_SECONDS:
        return False

    return not _articles_have_conflicting_rich_content(existing, candidate)


def _merge_articles(existing: Article, candidate: Article) -> Article:
    if _metadata_priority(candidate) > _metadata_priority(existing):
        primary = candidate
        secondary = existing
    else:
        primary = existing
        secondary = candidate

    merged_title = primary.title
    merged_source = primary.source

    if _is_default_published(existing.published_at):
        merged_published_at = candidate.published_at
    elif _is_default_published(candidate.published_at):
        merged_published_at = existing.published_at
    else:
        merged_published_at = min(existing.published_at, candidate.published_at)

    existing_freshness_at = existing.freshness_at or existing.published_at
    candidate_freshness_at = candidate.freshness_at or candidate.published_at
    trusted_freshness_candidates: list[datetime] = []
    if _is_trusted_article_source(existing) and not _is_default_published(
        existing_freshness_at
    ):
        trusted_freshness_candidates.append(existing_freshness_at)
    if _is_trusted_article_source(candidate) and not _is_default_published(
        candidate_freshness_at
    ):
        trusted_freshness_candidates.append(candidate_freshness_at)
    merged_freshness_at = (
        max(trusted_freshness_candidates)
        if trusted_freshness_candidates
        else max(existing_freshness_at, candidate_freshness_at)
    )
    merged_freshness_at = max(merged_freshness_at, merged_published_at)

    merged_summary = primary.summary or secondary.summary
    merged_excerpt = primary.excerpt or secondary.excerpt

    return Article(
        id=existing.id,
        source=merged_source,
        title=merged_title,
        url=primary.url,
        published_at=merged_published_at,
        freshness_at=merged_freshness_at,
        summary=merged_summary,
        excerpt=merged_excerpt,
    )


async def _fetch(client: httpx.AsyncClient, url: str) -> bytes | None:
    try:
        r = await client.get(
            url, timeout=config.REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}
        )
        r.raise_for_status()
        return r.content
    except Exception as e:  # broad log; upstream handles partial
        logger.warning(f"fetch failed {url}: {e}")
        return None


async def fetch_all_feeds(urls: List[str]) -> List[RawFeedItem]:
    items: List[RawFeedItem] = []
    limits = asyncio.Semaphore(config.FETCH_CONCURRENCY)
    async with httpx.AsyncClient(follow_redirects=True) as client:

        async def task(u: str):
            async with limits:
                data = await _fetch(client, u)
                if not data:
                    return
                feed = feedparser.parse(data)
                for e in feed.entries:
                    pub = _extract_published_datetime(e)
                    freshness = _extract_freshness_datetime(e)
                    items.append(
                        RawFeedItem(
                            source=u,
                            title=getattr(e, "title", "").strip(),
                            link=getattr(e, "link", ""),
                            published=pub,
                            updated=freshness,
                            summary=getattr(e, "summary", None),
                            content=(
                                getattr(e, "content", [{}])[0].get("value")
                                if getattr(e, "content", None)
                                else None
                            ),
                        )
                    )

        await asyncio.gather(*(task(u) for u in urls))
    return items


_DEF_PUB_DT = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _raw_item_sort_key(item: RawFeedItem) -> tuple[str, str, int, int, str, str]:
    title = item.title or "(no title)"
    published = (_ensure_timezone(item.published) or _DEF_PUB_DT).astimezone(
        timezone.utc
    )
    freshness = (_ensure_timezone(item.updated) or published).astimezone(timezone.utc)
    resolved_link = _resolved_link(str(item.link), item.source)
    canonical_url = _canonicalize_url(resolved_link)
    return (
        canonical_url,
        _normalized_title_key(title),
        int(published.timestamp()),
        int(freshness.timestamp()),
        item.source,
        resolved_link,
    )


def normalize(raw_items: List[RawFeedItem]) -> List[Article]:
    articles_by_key: dict[str, Article] = {}
    canonical_groups: dict[str, list[str]] = {}
    for r in sorted(raw_items, key=_raw_item_sort_key):
        title = r.title or "(no title)"
        pub = _ensure_timezone(r.published) or _DEF_PUB_DT
        pub = pub.astimezone(timezone.utc)
        freshness = _ensure_timezone(r.updated) or pub
        freshness = freshness.astimezone(timezone.utc)
        resolved_link = _resolved_link(str(r.link), r.source)
        canonical_url = _canonicalize_url(resolved_link)
        article_key = _article_key(resolved_link, r.source, title, pub)
        summary = strip_html(r.summary or r.content or "")[:400]
        excerpt = make_excerpt(r.summary, r.content)
        candidate = Article(
            id="",
            source=r.source,
            title=title,
            url=resolved_link,
            published_at=pub,
            freshness_at=pub,
            summary=summary,
            excerpt=excerpt,
        )
        if _is_trusted_article_source(candidate):
            candidate = candidate.model_copy(
                update={"freshness_at": _bounded_trusted_freshness(pub, freshness)}
            )

        canonical_split = _safe_urlsplit(canonical_url)
        if (
            canonical_split is not None
            and canonical_split.scheme
            and canonical_split.netloc
        ):
            group_keys = canonical_groups.setdefault(article_key, [])
            matched_key = next(
                (
                    key
                    for key in group_keys
                    if _should_merge_articles(articles_by_key[key], candidate)
                ),
                None,
            )
            if matched_key is None:
                final_key = (
                    article_key
                    if not group_keys
                    else _disambiguated_article_key(candidate)
                )
                articles_by_key[final_key] = candidate.model_copy(
                    update={
                        "id": hashlib.sha256(final_key.encode()).hexdigest()[:16],
                    }
                )
                group_keys.append(final_key)
            else:
                merged = _merge_articles(articles_by_key[matched_key], candidate)
                articles_by_key[matched_key] = merged.model_copy(
                    update={
                        "id": hashlib.sha256(matched_key.encode()).hexdigest()[:16],
                    }
                )
            continue

        existing = articles_by_key.get(article_key)
        if existing is None:
            articles_by_key[article_key] = candidate.model_copy(
                update={"id": hashlib.sha256(article_key.encode()).hexdigest()[:16]}
            )
        else:
            articles_by_key[article_key] = _merge_articles(existing, candidate)
    return list(articles_by_key.values())
