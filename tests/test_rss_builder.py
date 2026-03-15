import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timezone
from src import config
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


def test_build_rss_handles_malformed_urls_without_crashing():
    article = make_ranked(1).model_copy(update={"url": "https://[broken-url/story-1"})

    xml = build_rss([article])

    assert "https://example.com" in xml


def test_build_rss_replaces_non_http_links_with_site_url():
    article = make_ranked(1).model_copy(update={"url": "javascript:alert(1)"})

    xml = build_rss([article])

    assert "javascript:alert(1)" not in xml
    assert config.SITE_BASE_URL.rstrip("/") in xml


def test_build_rss_replaces_urls_with_embedded_credentials():
    article = make_ranked(1).model_copy(
        update={"url": "https://user:pass@example.com/private"}
    )

    xml = build_rss([article])

    assert "user:pass@" not in xml
    assert config.SITE_BASE_URL.rstrip("/") in xml


def test_build_rss_strips_tracking_parameters_from_public_links():
    article = make_ranked(1).model_copy(
        update={"url": "https://example.com/x?b=2&utm_source=hatena&a=1#frag"}
    )

    xml = build_rss([article])

    assert "utm_source" not in xml
    assert "#frag" not in xml
    assert "https://example.com/x?a=1&amp;b=2" in xml


def test_build_rss_safely_handles_cdata_terminator_in_content():
    base = make_ranked(1)
    article = base.model_copy(
        update={
            "summary": "Summary with ]]> terminator",
            "excerpt": "Excerpt with ]]> marker",
            "scores": base.scores.model_copy(update={"reason": "Reason with ]]> marker"}),
        }
    )

    xml = build_rss([article])

    assert "<description><![CDATA[" in xml
    assert "]]&gt;" in xml
