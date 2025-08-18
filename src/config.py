from __future__ import annotations
import os
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

FEED_URLS: List[str] = [
    "https://zenn.dev/feed",
    "https://codezine.jp/rss/new/20/index.xml",
    "https://qiita.com/popular-items/feed",
]
TOP_N: int = 30
REQUEST_TIMEOUT: float = 15.0
FETCH_CONCURRENCY: int = 5
SCORE_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
RETRY_MAX: int = 2
LLM_TEMPERATURE: float = 0.1
MAX_SCORE_RETRY: int = 2
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
OUTPUT_RSS_PATH: str = os.getenv("OUTPUT_RSS_PATH", "docs/rss.xml")
CACHE_DIR: str = os.getenv("CACHE_DIR", ".cache")
SCORE_CONCURRENCY: int = 3
SITE_BASE_URL: str = os.getenv("SITE_BASE_URL", "https://example.com/")

os.makedirs(CACHE_DIR, exist_ok=True)
