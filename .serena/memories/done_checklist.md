---
applyTo: '**'
---

# When finishing a change

- Run `python -m pytest tests/ -v` (or VS Code task "Run Tests").
- If RSS output format changed, regenerate `docs/rss.xml` and sanity-check a reader fetch.
- Keep changes minimal and focused; avoid reformatting unrelated code.
