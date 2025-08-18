from __future__ import annotations
from datetime import datetime, timezone
from xml.sax.saxutils import escape
from .models import RankedArticle
from . import config
from email.utils import format_datetime

RSS_HEADER = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"

def build_rss(articles: list[RankedArticle]) -> str:
    now = format_datetime(datetime.now(timezone.utc))
    channel_parts = [
        "<channel>",
        "<title>Tech Curated Top 30</title>",
    f"<link>{escape(config.SITE_BASE_URL)}</link>",
        "<description>Ranked top technical articles</description>",
        f"<lastBuildDate>{now}</lastBuildDate>",
        "<language>ja</language>",
    ]
    item_xml: list[str] = []
    for a in articles:
        pub = format_datetime(a.published_at.replace(tzinfo=timezone.utc))
        desc = escape(f"{a.summary}\nScore: {a.total} (N={a.scores.novelty}/I={a.scores.interest}/E={a.scores.expertise})\nReason: {a.scores.reason}\nExcerpt: {a.excerpt}")
        item_parts = [
            "<item>",
            f"<title>{escape(a.title)}</title>",
            f"<link>{escape(str(a.url))}</link>",
            f"<guid isPermaLink=\"false\">{escape(a.id)}</guid>",
            f"<pubDate>{pub}</pubDate>",
            f"<description>{desc}</description>",
            f"<category>Score:{a.total}</category>",
            "</item>",
        ]
        item_xml.append("".join(item_parts))
    channel_parts.extend(item_xml)
    channel_parts.append("</channel>")
    return f"{RSS_HEADER}<rss version=\"2.0\">{''.join(channel_parts)}</rss>"
