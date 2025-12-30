---
applyTo: '**'
---

# Suggested commands (Darwin/macOS)

Install deps:
- `pip install -r requirements.txt`

Run system:
- `source .env && PYTHONPATH=. python -m src.main`

Run tests:
- `python -m pytest tests/ -v`

Cleanup bytecode:
- `find . -name '*.pyc' -delete && find . -name '__pycache__' -type d -exec rm -rf {} +`

Notes:
- Requires `OPENAI_API_KEY` in `.env` for scoring; tests that need the key should skip when unset.
