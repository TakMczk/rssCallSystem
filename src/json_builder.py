from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Iterable

from .models import RankedArticle


def _isoformat_z(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_json_feed(
    ranked_articles: Iterable[RankedArticle], generated_at: datetime | None = None
) -> str:
    generated_at = generated_at or datetime.now(timezone.utc)
    articles = list(ranked_articles)
    payload = {
        "schemaVersion": "1.0",
        "generatedAt": _isoformat_z(generated_at),
        "articles": [
            {
                "rank": index,
                "id": article.id,
                "title": article.title,
                "url": str(article.url),
                "source": article.source,
                "publishedAt": _isoformat_z(article.published_at),
                "freshnessAt": _isoformat_z(article.freshness_at),
                "summaryJa": article.scores.summary_ja,
                "excerpt": article.excerpt,
                "reason": article.scores.reason,
                "techScore": article.scores.tech_score,
                "cultureScore": article.scores.culture_score,
                "scores": {
                    "total": article.scores.total,
                    "novelty": article.scores.novelty,
                    "interest": article.scores.interest,
                    "expertise": article.scores.expertise,
                    "culturalRelevance": article.scores.cultural_relevance,
                    "lifestyleConnection": article.scores.lifestyle_connection,
                    "creativity": article.scores.creativity,
                },
            }
            for index, article in enumerate(articles, start=1)
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
