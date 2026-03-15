from __future__ import annotations
import math
from collections import Counter
from datetime import datetime, timezone
from typing import List
from urllib.parse import SplitResult, urlsplit

from . import config
from .models import RankedArticle


def _resolve_now(now: datetime | None) -> datetime:
    return now or datetime.now(timezone.utc)


def _effective_freshness_at(article: RankedArticle, now: datetime) -> datetime:
    return min(article.freshness_at or article.published_at, now)


def _age_hours(article: RankedArticle, now: datetime) -> float:
    freshness_at = _effective_freshness_at(article, now)
    return max(
        0.0,
        (now - freshness_at.astimezone(timezone.utc)).total_seconds() / 3600,
    )


def _freshness_bonus(article: RankedArticle, now: datetime) -> float:
    if not config.RANKING_ENABLE_HYBRID:
        return 0.0

    if config.RANKING_FRESHNESS_HALF_LIFE_HOURS <= 0:
        return 0.0

    decay = math.exp(
        -math.log(2)
        * _age_hours(article, now)
        / config.RANKING_FRESHNESS_HALF_LIFE_HOURS
    )
    return config.RANKING_FRESHNESS_MAX_BONUS * decay


def _rank_value(
    article: RankedArticle, now: datetime, source_penalty: float = 0.0
) -> tuple[float, int, int, int, int, float, str]:
    freshness_at = _effective_freshness_at(article, now)
    return (
        article.total + _freshness_bonus(article, now) - source_penalty,
        article.total,
        article.scores.novelty,
        article.scores.expertise,
        article.scores.interest,
        freshness_at.timestamp(),
        article.id,
    )


def _sort_preliminary(
    articles: List[RankedArticle], now: datetime
) -> List[RankedArticle]:
    return sorted(articles, key=lambda article: _rank_value(article, now), reverse=True)


def _safe_urlsplit(value: str) -> SplitResult | None:
    try:
        return urlsplit(value)
    except ValueError:
        return None


def _normalized_host(split: SplitResult) -> str:
    hostname = (split.hostname or "").lower()
    if hostname.startswith("www."):
        return hostname[4:]
    return hostname


def _publisher_key(article: RankedArticle) -> str:
    parsed = _safe_urlsplit(str(article.url))
    if parsed is not None:
        hostname = _normalized_host(parsed)
        if hostname in {"zenn.dev", "qiita.com"}:
            path_parts = [segment for segment in parsed.path.split("/") if segment]
            if path_parts:
                return f"{hostname}/{path_parts[0].lower()}"
        if hostname:
            return hostname

    source_parsed = _safe_urlsplit(article.source)
    if source_parsed is not None:
        source_host = _normalized_host(source_parsed)
        if source_host:
            return source_host

    return article.source


def _sort_with_diversity(
    articles: List[RankedArticle], now: datetime
) -> List[RankedArticle]:
    remaining = _sort_preliminary(articles, now)
    selected: List[RankedArticle] = []
    source_counts: Counter[str] = Counter()

    while remaining:
        best_index = max(
            range(len(remaining)),
            key=lambda index: _rank_value(
                remaining[index],
                now,
                config.RANKING_SOURCE_REPEAT_PENALTY
                * source_counts[_publisher_key(remaining[index])],
            ),
        )
        best_article = remaining.pop(best_index)
        selected.append(best_article)
        source_counts[_publisher_key(best_article)] += 1

    return selected


def sort_ranked(
    articles: List[RankedArticle], now: datetime | None = None
) -> List[RankedArticle]:
    resolved_now = _resolve_now(now)
    if not config.RANKING_ENABLE_DIVERSITY:
        return _sort_preliminary(articles, resolved_now)
    return _sort_with_diversity(articles, resolved_now)
