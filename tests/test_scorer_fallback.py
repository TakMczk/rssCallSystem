import asyncio
from datetime import datetime, timezone
from src import scorer, config
from src.models import Article

def test_scorer_fallback_no_key(monkeypatch):
    # Force no API key
    monkeypatch.setattr(config, "GEMINI_API_KEY", None)
    art = Article(
        id="a1",
        source="s",
        title="Test Title",
        url="https://example.com/",
        published_at=datetime.now(timezone.utc),
        summary="Summary",
        excerpt="Excerpt",
    )

    async def run():
        result = await scorer.score_article(art)
        assert result.novelty == 5
        assert result.interest == 5
        assert result.expertise == 5
        assert "fallback" in result.reason

    asyncio.run(run())
