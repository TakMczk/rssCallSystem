from __future__ import annotations
from datetime import datetime
from typing import Union, Optional
from pydantic import BaseModel, HttpUrl

class RawFeedItem(BaseModel):
    source: str
    title: str
    link: Union[str, HttpUrl]
    published: Optional[datetime] = None
    summary: Optional[str] = None
    content: Optional[str] = None

class Article(BaseModel):
    id: str
    source: str
    title: str
    url: Union[str, HttpUrl]
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
