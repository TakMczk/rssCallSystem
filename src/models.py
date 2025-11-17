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
    # 技術面の評価（合計30点）
    novelty: int  # 新規性 0-10
    interest: int  # 興味深さ 0-10
    expertise: int  # 専門性 0-10
    
    # 文化面の評価（合計30点）
    cultural_relevance: int  # 文化的関連性 0-10
    lifestyle_connection: int  # 生活との接点 0-10
    creativity: int  # 創造性・芸術性 0-10
    
    reason: str

    @property
    def total(self) -> int:
        return (self.novelty + self.interest + self.expertise + 
                self.cultural_relevance + self.lifestyle_connection + self.creativity)
    
    @property
    def tech_score(self) -> int:
        """技術面の合計スコア（0-30）"""
        return self.novelty + self.interest + self.expertise
    
    @property
    def culture_score(self) -> int:
        """文化面の合計スコア（0-30）"""
        return self.cultural_relevance + self.lifestyle_connection + self.creativity

class RankedArticle(Article):
    scores: ScoreResult

    @property
    def total(self) -> int:  # convenience
        return self.scores.total
