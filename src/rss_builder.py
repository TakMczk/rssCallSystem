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
    channel_parts = [
        "<channel>",
        "<title>Tech Curated Top 30</title>",
    f"<link>{escape(config.SITE_BASE_URL)}</link>",
        "<description>Ranked top technical articles</description>",
        f"<lastBuildDate>{now_str}</lastBuildDate>",
        "<language>ja</language>",
    ]
    item_xml: list[str] = []
    for i, a in enumerate(articles, start=1):
        # Force order by manipulating pubDate (latest first)
        # We subtract 'i' minutes from the current time so rank 1 is newest, rank 2 is 1 min older, etc.
        fake_pub_dt = now_dt - timedelta(minutes=i)
        pub = format_datetime(fake_pub_dt)
        
        # Add rank and score to title for clarity
        title_with_score = f"[#{i} Score:{a.total}] {a.title}"
        
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
    return f"{RSS_HEADER}<rss version=\"2.0\">{''.join(channel_parts)}</rss>"
