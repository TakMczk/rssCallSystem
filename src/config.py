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
    "https://www.publickey1.jp/atom.xml",
    "https://www.technologyreview.jp/feed/",
    "https://feeds.japan.zdnet.com/rss/zdnet/all.rdf",
    "https://wirelesswire.jp/feed/",
    "https://wired.jp/rssfeeder/",
    "https://tech.nikkeibp.co.jp/rss/xtech-it.rdf",
]
TOP_N: int = 15
REQUEST_TIMEOUT: float = 15.0
FETCH_CONCURRENCY: int = 5
OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
OPENAI_ORGANIZATION: Optional[str] = os.getenv("OPENAI_ORGANIZATION")  # Organization ID for project keys
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-5-nano")  # Fastest, most cost-efficient GPT-5 model
RETRY_MAX: int = 2
LLM_TEMPERATURE: float = 0.1
MAX_SCORE_RETRY: int = 3  # Increase retry attempts
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
OUTPUT_RSS_PATH: str = os.getenv("OUTPUT_RSS_PATH", "docs/rss.xml")
CACHE_DIR: str = os.getenv("CACHE_DIR", ".cache")
SCORE_CONCURRENCY: int = 2  # Reduce concurrent requests to avoid rate limits
RATE_LIMIT_DELAY: float = 2.0  # Base delay for rate limit handling
BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "20"))  # Number of articles per batch (optimized for gpt-5-nano)
USE_BATCH_SCORING: bool = os.getenv("USE_BATCH_SCORING", "true").lower() == "true"
SITE_BASE_URL: str = os.getenv("SITE_BASE_URL", "https://example.com/")
TIME_WINDOW_HOURS: int = int(os.getenv("TIME_WINDOW_HOURS", "24"))  # Filter articles from the last N hours

os.makedirs(CACHE_DIR, exist_ok=True)
