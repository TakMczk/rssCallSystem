from __future__ import annotations
import re
from html import unescape
from typing import Optional

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

def strip_html(value: str) -> str:
    text = _TAG_RE.sub(" ", value)
    text = unescape(text)
    text = _WS_RE.sub(" ", text)
    return text.strip()

def make_excerpt(summary: Optional[str], content: Optional[str], max_len: int = 180) -> str:
    base = summary or content or ""
    base = strip_html(base)
    if len(base) > max_len:
        return base[: max_len - 1] + "…"
    return base
