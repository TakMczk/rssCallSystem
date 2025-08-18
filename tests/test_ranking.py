from datetime import datetime, timezone, timedelta
from src.models import Article, ScoreResult, RankedArticle
from src.ranking import sort_ranked

def make_article(total, novelty, expertise, interest, idx):
    a = Article(
        id=str(idx),
        source="x",
        title=f"t{idx}",
        url="https://example.com/x",
        published_at=datetime.now(timezone.utc) - timedelta(minutes=idx),
        summary="s",
        excerpt="e",
    )
    score = ScoreResult(novelty=novelty, interest=interest, expertise=expertise, reason="r")
    return RankedArticle(**a.model_dump(), scores=score)

def test_sort_ranked():
    arts = [
        make_article(20, 8, 7, 5, 1),
        make_article(25, 9, 9, 7, 2),
        make_article(25, 9, 8, 9, 3),
    ]
    sorted_ = sort_ranked(arts)
    # Highest total first (25, 25, 20); tie broken by novelty (both 9), then expertise (9 > 8)
    assert sorted_[0].scores.expertise == 9  # article 3: total=25, novelty=9, expertise=9
    assert sorted_[1].scores.expertise == 7  # article 2: total=25, novelty=9, expertise=8
    assert sorted_[2].scores.novelty == 8    # article 1: total=20, novelty=8
