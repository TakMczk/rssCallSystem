import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timezone
from src.rss_builder import build_rss
from src.models import RankedArticle, Article, ScoreResult

def make_ranked(i: int) -> RankedArticle:
    art = Article(
        id=f"id{i}",
        source="test",
        title=f"Title {i}",
        url="https://example.com/x",
        published_at=datetime.now(timezone.utc),
        summary="Summary",
        excerpt="Excerpt",
    )
    score = ScoreResult(
        novelty=7, interest=6, expertise=8,
        cultural_relevance=7, lifestyle_connection=6, creativity=8,
        reason="Reason"
    )
    return RankedArticle(**art.model_dump(), scores=score)

def test_build_rss_structure():
    xml = build_rss([make_ranked(1), make_ranked(2)])
    assert "<rss" in xml
    assert xml.count("<item>") == 2
    assert "Score:" in xml
    assert "Title 1" in xml
