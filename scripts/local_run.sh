#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${GEMINI_API_KEY:-}" ]]; then
  echo "[ERROR] GEMINI_API_KEY not set" >&2
  exit 1
fi

export GEMINI_MODEL="${GEMINI_MODEL:-gemini-1.5-flash}"
export SITE_BASE_URL="${SITE_BASE_URL:-https://example.com/}"

echo "[INFO] Using MODEL=$GEMINI_MODEL BASE=$SITE_BASE_URL"
python -m src.main

echo "[INFO] Output: docs/rss.xml"
