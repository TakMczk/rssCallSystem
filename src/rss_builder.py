from __future__ import annotations
from datetime import datetime, timezone, timedelta
from xml.sax.saxutils import escape
from .models import RankedArticle
from . import config
from email.utils import format_datetime

RSS_HEADER = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"

def build_rss(articles: list[RankedArticle]) -> str:
    now_dt = datetime.now(timezone.utc)
    now_str = format_datetime(now_dt)
    feed_url = f"{config.SITE_BASE_URL.rstrip('/')}/rss.xml"
    channel_parts = [
        "<channel>",
        "<title>Tech Curated Top 30</title>",
        f"<link>{escape(config.SITE_BASE_URL)}</link>",
        f"<atom:link href=\"{escape(feed_url)}\" rel=\"self\" type=\"application/rss+xml\" />",
        "<description>Ranked top technical articles</description>",
        f"<lastBuildDate>{now_str}</lastBuildDate>",
        "<language>ja</language>",
        "<ttl>60</ttl>",
    ]
    item_xml: list[str] = []
    for i, a in enumerate(articles, start=1):
        # Publish items in strict rank order with monotonically decreasing times
        # to avoid reader-side truncation when entries are not time-sorted. We
        # still include the original publication date inside the description.
        pub_dt = now_dt - timedelta(seconds=i)
        pub = format_datetime(pub_dt)
        
        # Add rank and score to title for clarity.
        # Place it at the end to avoid some readers' similarity/duplicate heuristics
        # collapsing items that share a common prefix.
        title_with_score = f"{a.title} [#{i} Score:{a.total}]"
        
        # Include original publication date in description
        original_date_str = a.published_at.strftime('%Y-%m-%d %H:%M')
        
        # Use HTML for description to ensure proper formatting in RSS readers
        summary_html = f"<p>{escape(a.summary)}</p>" if a.summary else ""
        reason_html = f"<p><strong>Reason:</strong> {escape(a.scores.reason)}</p>"
        
        score_detail = (
            f"Tech: N={a.scores.novelty}/I={a.scores.interest}/E={a.scores.expertise}, "
            f"Culture: C={a.scores.cultural_relevance}/L={a.scores.lifestyle_connection}/Cr={a.scores.creativity}"
        )
        score_html = f"<p><strong>Score: {a.total}</strong> <small>({score_detail})</small></p>"
        
        excerpt_html = f"<p><strong>Excerpt:</strong> {escape(a.excerpt)}</p>" if a.excerpt else ""
        original_date_html = f"<p><small>Original PubDate: {original_date_str}</small></p>"

        # Combine into a CDATA block for the description
        description_content = f"{summary_html}{reason_html}{score_html}{excerpt_html}{original_date_html}"
        
        item_parts = [
            "<item>",
            f"<title>{escape(title_with_score)}</title>",
            f"<link>{escape(str(a.url))}</link>",
            f"<guid isPermaLink=\"false\">{escape(a.id)}</guid>",
            f"<pubDate>{pub}</pubDate>",
            f"<description><![CDATA[{description_content}]]></description>",
            f"<category>Score:{a.total}</category>",
            "</item>",
        ]
        item_xml.append("".join(item_parts))
    channel_parts.extend(item_xml)
    channel_parts.append("</channel>")
    return f"{RSS_HEADER}<rss version=\"2.0\" xmlns:atom=\"http://www.w3.org/2005/Atom\">{''.join(channel_parts)}</rss>"
