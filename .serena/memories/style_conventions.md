---
applyTo: '**'
---

# Style & conventions

- Language: Python.
- Prefer clear, small functions and minimal dependencies.
- Configuration via `src/config.py` with environment-variable overrides.
- Tests: pytest under `tests/`; avoid tests that hard-require external API unless gated by `OPENAI_API_KEY`.
