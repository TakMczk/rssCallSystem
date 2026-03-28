from __future__ import annotations
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta

from . import config
from .fetcher import _DEF_PUB_DT, fetch_all_feeds, normalize
from .json_builder import build_json_feed
from .scorer import score_articles
from .ranking import sort_ranked
from .rss_builder import build_rss
from .models import RankedArticle, Article
from .logging_utils import get_logger

logger = get_logger(__name__)
_MAX_DEFAULT_PUBLISHED_FUTURE_SKEW = timedelta(hours=1)


def _recent_article_grace_cutoff(current_time: datetime, hours: int) -> datetime:
    return current_time - timedelta(hours=hours * 2)


def _effective_recent_at(article: Article, current_time: datetime) -> datetime:
    freshness_at = article.freshness_at or article.published_at
    if (
        article.published_at == _DEF_PUB_DT
        and freshness_at > current_time + _MAX_DEFAULT_PUBLISHED_FUTURE_SKEW
    ):
        return article.published_at
    return min(freshness_at, current_time)


def filter_recent_articles(articles: list[Article], hours: int) -> list[Article]:
    """Filter recently published articles, with a bounded grace period for updates."""
    current_time = datetime.now(timezone.utc)
    cutoff_time = current_time - timedelta(hours=hours)
    grace_cutoff = _recent_article_grace_cutoff(current_time, hours)
    filtered = [
        a
        for a in articles
        if a.published_at >= cutoff_time
        or (
            a.published_at == _DEF_PUB_DT
            and _effective_recent_at(a, current_time) >= cutoff_time
        )
        or (
            a.published_at >= grace_cutoff
            and _effective_recent_at(a, current_time) >= cutoff_time
        )
    ]
    logger.info(
        f"filtered articles: {len(articles)} -> {len(filtered)} (within {hours} hours)"
    )
    return filtered


async def run():
    logger.info("start pipeline")
    out_path = Path(config.OUTPUT_RSS_PATH)
    json_path = Path(config.OUTPUT_JSON_PATH)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    raw = await fetch_all_feeds(config.FEED_URLS)
    logger.info(f"fetched raw items: {len(raw)}")
    articles = normalize(raw)
    logger.info(f"normalized unique items: {len(articles)}")
    pre_filter_count = len(articles)

    # Filter articles to only those published within the configured time window
    articles = filter_recent_articles(articles, config.TIME_WINDOW_HOURS)

    if not articles:
        logger.warning("no articles found within the time window")
        if pre_filter_count > 0:
            generated_at = datetime.now(timezone.utc)
            out_path.write_text(build_rss([]), encoding="utf-8")
            json_path.write_text(build_json_feed([], generated_at=generated_at), encoding="utf-8")
            logger.info(f"wrote rss: {out_path} (0 items)")
            logger.info(f"wrote json: {json_path} (0 items)")
        else:
            logger.warning(
                "skipping outputs overwrite because fetch/normalize produced no items"
            )
        return

    scores = await score_articles(articles)
    ranked: list[RankedArticle] = []
    for a, s in zip(articles, scores):
        ranked.append(RankedArticle(**a.model_dump(), scores=s))
    ranked_sorted = sort_ranked(ranked)[: config.TOP_N]
    generated_at = datetime.now(timezone.utc)
    rss_xml = build_rss(ranked_sorted)
    json_text = build_json_feed(ranked_sorted, generated_at=generated_at)
    out_path.write_text(rss_xml, encoding="utf-8")
    json_path.write_text(json_text, encoding="utf-8")
    logger.info(f"wrote rss: {out_path} ({len(ranked_sorted)} items)")
    logger.info(f"wrote json: {json_path} ({len(ranked_sorted)} items)")


if __name__ == "__main__":
    asyncio.run(run())
