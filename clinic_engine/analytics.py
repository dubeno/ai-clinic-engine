from datetime import datetime

from loguru import logger

from .db import Database
from .models import ArticleAnalytics


class AnalyticsTracker:
    def __init__(self, db: Database | None = None):
        self.db = db or Database()

    def record_publish(self, article_id: int, platform: str, url: str | None = None) -> int:
        analytics = ArticleAnalytics(
            article_id=article_id,
            published_at=datetime.now(),
            platform=platform,
        )
        row_id = self.db.insert_analytics(analytics)
        logger.info(f"记录发布: article_id={article_id}, platform={platform}")
        return row_id

    def get_summary(self) -> dict:
        return self.db.get_analytics_summary()

    def update_stats(self, article_id: int, views: int = 0, clicks: int = 0, shares: int = 0):
        logger.info(f"更新统计: article_id={article_id}, views={views}, clicks={clicks}")
