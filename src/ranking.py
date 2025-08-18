from __future__ import annotations
from typing import List
from .models import RankedArticle

def sort_ranked(articles: List[RankedArticle]) -> List[RankedArticle]:
    return sorted(
        articles,
        key=lambda a: (
            -a.total,
            -a.scores.novelty,
            -a.scores.expertise,
            -a.scores.interest,
            a.published_at.timestamp() * -1,
        ),
    )
