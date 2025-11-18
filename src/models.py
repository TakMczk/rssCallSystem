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
    # 技術面の評価（各0-10点、合計40点相当）
    novelty: int  # 新規性 0-10
    interest: int  # 興味深さ 0-10
    expertise: int  # 専門性 0-10
    
    # 文化面の評価（各0-10点、合計20点相当）
    cultural_relevance: int  # 文化的関連性 0-10
    lifestyle_connection: int  # 生活との接点 0-10
    creativity: int  # 創造性・芸術性 0-10
    
    reason: str

    @property
    def total(self) -> int:
        """合計スコア（60点満点: テクノロジー40点 + 文化20点）"""
        tech = self.novelty + self.interest + self.expertise  # 0-30
        culture = self.cultural_relevance + self.lifestyle_connection + self.creativity  # 0-30
        # 技術を1.33倍、文化を0.67倍で40:20の比率に調整
        return round(tech * 4 / 3 + culture * 2 / 3)
    
    @property
    def tech_score(self) -> int:
        """技術面の合計スコア（0-30、40点相当に換算）"""
        return self.novelty + self.interest + self.expertise
    
    @property
    def culture_score(self) -> int:
        """文化面の合計スコア（0-30、20点相当に換算）"""
        return self.cultural_relevance + self.lifestyle_connection + self.creativity

class RankedArticle(Article):
    scores: ScoreResult

    @property
    def total(self) -> int:  # convenience
        return self.scores.total
