from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ArticleStatus(str, Enum):
    DRAFT = "draft"
    QUALITY_CHECKED = "quality_checked"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ContentType(str, Enum):
    SEO_ARTICLE = "seo_article"
    WECHAT = "wechat"
    XIAOHONGSHU = "xiaohongshu"


CONTENT_TYPE_NAMES = {
    ContentType.SEO_ARTICLE: "百度SEO文章",
    ContentType.WECHAT: "微信公众号文章",
    ContentType.XIAOHONGSHU: "小红书笔记",
}


def get_specialty_names() -> dict:
    """获取当前行业的专科名称映射"""
    from .industries import get_profile
    return get_profile().specialty_names


class Topic(BaseModel):
    id: Optional[int] = None
    keyword: str
    search_volume: int = 0
    competition: float = 0.0
    relevance_score: float = 0.0
    related_keywords: list[str] = []
    content_type: ContentType = ContentType.SEO_ARTICLE
    specialty: str = "general"
    priority_score: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)
    status: str = "queued"


class QualityIssue(BaseModel):
    rule: str
    severity: str  # "error", "warning", "info"
    message: str
    location: Optional[str] = None


class QualityResult(BaseModel):
    passed: bool
    issues: list[QualityIssue] = []
    checked_at: datetime = Field(default_factory=datetime.now)


class Article(BaseModel):
    id: Optional[int] = None
    topic_id: Optional[int] = None
    title: str
    content: str
    html_content: Optional[str] = None
    content_type: ContentType = ContentType.SEO_ARTICLE
    specialty: str = "general"
    status: ArticleStatus = ArticleStatus.DRAFT
    quality_result: Optional[QualityResult] = None
    review_notes: Optional[str] = None
    reviewer_name: Optional[str] = None
    published_at: Optional[datetime] = None
    published_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ArticleAnalytics(BaseModel):
    article_id: int
    published_at: datetime
    platform: str
    views: int = 0
    clicks: int = 0
    shares: int = 0
    last_updated: datetime = Field(default_factory=datetime.now)


# 向后兼容
def __getattr__(name):
    if name == "MedicalSpecialty":
        from .industries.medical.profile import MedicalSpecialty
        return MedicalSpecialty
    if name == "SPECIALTY_NAMES":
        return get_specialty_names()
    raise AttributeError(name)
