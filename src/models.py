from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, HttpUrl

class RawFeedItem(BaseModel):
    source: str
    title: str
    link: str | HttpUrl
    published: datetime | None = None
    summary: str | None = None
    content: str | None = None

class Article(BaseModel):
    id: str
    source: str
    title: str
    url: str | HttpUrl
    published_at: datetime
    summary: str
    excerpt: str

class ScoreResult(BaseModel):
    novelty: int
    interest: int
    expertise: int
    reason: str

    @property
    def total(self) -> int:
        return self.novelty + self.interest + self.expertise

class RankedArticle(Article):
    scores: ScoreResult

    @property
    def total(self) -> int:  # convenience
        return self.scores.total
