from __future__ import annotations
import os
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def default_openai_reasoning_effort(model: str) -> Optional[str]:
    normalized = model.strip().lower()
    if not normalized.startswith("gpt-5"):
        return None
    if normalized.startswith(("gpt-5.4", "gpt-5.2")):
        return "none"
    return "minimal"


def _resolve_openai_reasoning_effort() -> Optional[str]:
    override = os.getenv("OPENAI_REASONING_EFFORT")
    if override is not None:
        override = override.strip()
        return override or None
    return default_openai_reasoning_effort(os.getenv("OPENAI_MODEL", "gpt-5-nano"))


def openai_cache_namespace(
    model: Optional[str] = None, reasoning_effort: Optional[str] = None
) -> str:
    resolved_model = (model or OPENAI_MODEL).strip().lower()
    resolved_effort = (
        OPENAI_REASONING_EFFORT if reasoning_effort is None else reasoning_effort
    )
    return f"{resolved_model}|{resolved_effort or 'default'}"

FEED_URLS: List[str] = [
    "https://zenn.dev/feed",
    "https://codezine.jp/rss/new/20/index.xml",
    "https://qiita.com/popular-items/feed",
    "https://www.publickey1.jp/atom.xml",
    "https://hnrss.org/best",
    "https://lobste.rs/rss",
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://www.theverge.com/rss/index.xml",
    "https://www.technologyreview.jp/feed/",
    "https://feeds.japan.zdnet.com/rss/zdnet/all.rdf",
    "https://wirelesswire.jp/feed/",
    "https://wired.jp/rssfeeder/",
    "https://xenospectrum.com/feed/",
    "https://tech.nikkeibp.co.jp/rss/xtech-it.rdf",
    "https://b.hatena.ne.jp/hotentry/it.rss",
]
TOP_N: int = 15
REQUEST_TIMEOUT: float = 15.0
FETCH_CONCURRENCY: int = 5
OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
OPENAI_ORGANIZATION: Optional[str] = os.getenv(
    "OPENAI_ORGANIZATION"
)  # Organization ID for project keys
# Default model: GPT-5.4-nano. The GPT-5.4 family uses `none` as the lowest-cost
# reasoning setting in Chat Completions, while older GPT-5 models use `minimal`.
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-5.4-nano")
OPENAI_REASONING_EFFORT: Optional[str] = _resolve_openai_reasoning_effort()
RETRY_MAX: int = 2

MAX_SCORE_RETRY: int = 3  # Increase retry attempts
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
OUTPUT_RSS_PATH: str = os.getenv("OUTPUT_RSS_PATH", "docs/rss.xml")
OUTPUT_JSON_PATH: str = os.getenv("OUTPUT_JSON_PATH", "docs/data.json")
OUTPUT_HISTORY_DIR: str = os.getenv("OUTPUT_HISTORY_DIR", "docs/history")
OUTPUT_HISTORY_INDEX_PATH: str = os.getenv(
    "OUTPUT_HISTORY_INDEX_PATH", "docs/history/index.json"
)
CACHE_DIR: str = os.getenv("CACHE_DIR", ".cache")
SCORE_CONCURRENCY: int = 2  # Reduce concurrent requests to avoid rate limits
RATE_LIMIT_DELAY: float = 2.0  # Base delay for rate limit handling
BATCH_SIZE: int = int(
    os.getenv("BATCH_SIZE", "20")
)  # Number of articles per batch (tuned for GPT-5 family batch scoring)
USE_BATCH_SCORING: bool = os.getenv("USE_BATCH_SCORING", "true").lower() == "true"
SITE_BASE_URL: str = os.getenv("SITE_BASE_URL", "https://example.com/")
TIME_WINDOW_HOURS: int = int(
    os.getenv("TIME_WINDOW_HOURS", "24")
)  # Filter articles from the last N hours
RANKING_ENABLE_HYBRID: bool = (
    os.getenv("RANKING_ENABLE_HYBRID", "true").lower() == "true"
)
RANKING_ENABLE_DIVERSITY: bool = (
    os.getenv("RANKING_ENABLE_DIVERSITY", "true").lower() == "true"
)
RANKING_FRESHNESS_HALF_LIFE_HOURS: float = float(
    os.getenv("RANKING_FRESHNESS_HALF_LIFE_HOURS", "18.0")
)
RANKING_FRESHNESS_MAX_BONUS: float = float(
    os.getenv("RANKING_FRESHNESS_MAX_BONUS", "6.0")
)
RANKING_SOURCE_REPEAT_PENALTY: float = float(
    os.getenv("RANKING_SOURCE_REPEAT_PENALTY", "1.5")
)
SCORER_CACHE_VERSION: str = os.getenv("SCORER_CACHE_VERSION", "v5")

# Some RSS readers (and Inoreader's optional "duplicate filters") can hide items
# if they consider them duplicates across feeds/folders/account. When enabled,
# we make per-item links unique by appending a stable query parameter.
RSS_DEDUPLICATE_LINKS: bool = (
    os.getenv("RSS_DEDUPLICATE_LINKS", "true").lower() == "true"
)
RSS_DEDUP_PARAM_KEY: str = os.getenv("RSS_DEDUP_PARAM_KEY", "rcs_id")

os.makedirs(CACHE_DIR, exist_ok=True)
