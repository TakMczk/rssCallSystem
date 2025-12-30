---
applyTo: '**'
---

# rssCallSystem overview

Purpose: Collect technical articles from multiple RSS feeds, score/rank them with OpenAI (default model: GPT-5-nano), and generate a ranked RSS feed at `docs/rss.xml` (for GitHub Pages).

Tech stack:
- Python 3.9+
- RSS parsing + feed aggregation (see `src/fetcher.py`)
- OpenAI Chat Completions for scoring (see `src/scorer.py`)
- Pytest tests under `tests/`

High-level flow:
`src/main.py` orchestrates: fetch -> normalize/dedupe -> time window filter -> score (batch) -> sort -> top N -> build RSS.

Key files:
- `src/config.py`: knobs like `TOP_N`, `TIME_WINDOW_HOURS`, `SITE_BASE_URL`, output path.
- `src/rss_builder.py`: RSS 2.0 generation (channel metadata + items).
- `docs/rss.xml`: generated feed, served via GitHub Pages.
