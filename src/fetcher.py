from __future__ import annotations
import asyncio
import hashlib
from datetime import datetime, timezone
from typing import List
import feedparser
import httpx
from dateutil import parser as dateparser

from .models import RawFeedItem, Article
from . import config
from .parser_utils import make_excerpt, strip_html
from .logging_utils import get_logger

logger = get_logger(__name__)

USER_AGENT = "TechCuratorBot/0.1 (+https://example.com)"

async def _fetch(client: httpx.AsyncClient, url: str) -> bytes | None:
    try:
        r = await client.get(url, timeout=config.REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
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
                    pub = None
                    if getattr(e, 'published', None):
                        try:
                            pub = dateparser.parse(e.published)
                        except Exception:
                            pub = None
                    items.append(
                        RawFeedItem(
                            source=u,
                            title=getattr(e, 'title', '').strip(),
                            link=getattr(e, 'link', ''),
                            published=pub,
                            summary=getattr(e, 'summary', None),
                            content=getattr(e, 'content', [{}])[0].get('value') if getattr(e, 'content', None) else None,
                        )
                    )
        await asyncio.gather(*(task(u) for u in urls))
    return items

_DEF_PUB_DT = datetime(1970, 1, 1, tzinfo=timezone.utc)

def normalize(raw_items: List[RawFeedItem]) -> List[Article]:
    seen: set[str] = set()
    out: List[Article] = []
    for r in raw_items:
        title = r.title or "(no title)"
        pub = r.published or _DEF_PUB_DT
        pub = pub.astimezone(timezone.utc)
        key_src = f"{r.link}|{title}|{int(pub.timestamp())}"
        id_ = hashlib.sha256(key_src.encode()).hexdigest()[:16]
        if id_ in seen:
            continue
        seen.add(id_)
        summary = strip_html(r.summary or r.content or "")[:400]
        excerpt = make_excerpt(r.summary, r.content)
        out.append(
            Article(
                id=id_,
                source=r.source,
                title=title,
                url=r.link,
                published_at=pub,
                summary=summary,
                excerpt=excerpt,
            )
        )
    return out
