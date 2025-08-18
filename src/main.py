from __future__ import annotations
import asyncio
from pathlib import Path

from . import config
from .fetcher import fetch_all_feeds, normalize
from .scorer import score_articles
from .ranking import sort_ranked
from .rss_builder import build_rss
from .models import RankedArticle
from .logging_utils import get_logger

logger = get_logger(__name__)

async def run():
    logger.info("start pipeline")
    raw = await fetch_all_feeds(config.FEED_URLS)
    logger.info(f"fetched raw items: {len(raw)}")
    articles = normalize(raw)
    logger.info(f"normalized unique items: {len(articles)}")
    scores = await score_articles(articles)
    ranked: list[RankedArticle] = []
    for a, s in zip(articles, scores):
        ranked.append(RankedArticle(**a.model_dump(), scores=s))
    ranked_sorted = sort_ranked(ranked)[: config.TOP_N]
    rss_xml = build_rss(ranked_sorted)
    out_path = Path(config.OUTPUT_RSS_PATH)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rss_xml, encoding="utf-8")
    logger.info(f"wrote rss: {out_path} ({len(ranked_sorted)} items)")

if __name__ == "__main__":
    asyncio.run(run())
