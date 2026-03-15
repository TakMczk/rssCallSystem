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


def make_excerpt(
    summary: Optional[str], content: Optional[str], max_len: int = 180
) -> str:
    summary_text = strip_html(summary or "")
    content_text = strip_html(content or "")
    base = content_text if len(content_text) >= len(summary_text) else summary_text
    if len(base) > max_len:
        return base[: max_len - 1] + "…"
    return base
