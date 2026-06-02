from loguru import logger

from .db import Database
from .models import Article, ArticleStatus


class ReviewManager:
    def __init__(self, db: Database | None = None):
        self.db = db or Database()

    def list_articles(self, status: str | ArticleStatus | None = None, limit: int = 50) -> list[Article]:
        if status is None:
            return self.db.get_articles_by_status(ArticleStatus.QUALITY_CHECKED, limit)
        if isinstance(status, str):
            status = ArticleStatus(status)
        return self.db.get_articles_by_status(status, limit)

    def approve(self, article_id: int, reviewer: str, notes: str | None = None) -> Article:
        article = self.db.get_article(article_id)
        if not article:
            raise ValueError(f"文章不存在: id={article_id}")

        # Warn if quality check had errors
        if article.quality_result and not article.quality_result.passed:
            error_count = sum(1 for i in article.quality_result.issues if i.severity == "error")
            logger.warning(f"文章有 {error_count} 个质量检查错误，但医生已选择通过审核")

        self.db.update_article_status(
            article_id,
            ArticleStatus.PENDING_REVIEW,
            review_notes=notes,
            reviewer_name=reviewer,
        )

        # Auto-approve to approved status (doctor has reviewed)
        self.db.update_article_status(article_id, ArticleStatus.APPROVED)

        logger.success(f"文章已审核通过: id={article_id}, 审核人={reviewer}")
        return self.db.get_article(article_id)

    def reject(self, article_id: int, reviewer: str, notes: str) -> Article:
        article = self.db.get_article(article_id)
        if not article:
            raise ValueError(f"文章不存在: id={article_id}")

        # Reset to draft for regeneration
        self.db.update_article_status(
            article_id,
            ArticleStatus.DRAFT,
            review_notes=notes,
            reviewer_name=reviewer,
        )

        logger.info(f"文章已打回: id={article_id}, 审核人={reviewer}, 备注={notes}")
        return self.db.get_article(article_id)

    def add_notes(self, article_id: int, notes: str) -> Article:
        article = self.db.get_article(article_id)
        if not article:
            raise ValueError(f"文章不存在: id={article_id}")

        existing = article.review_notes or ""
        timestamped = f"[备注] {notes}"
        combined = f"{existing}\n{timestamped}" if existing else timestamped

        self.db.update_article_status(
            article_id,
            article.status,
            review_notes=combined,
        )

        logger.info(f"已添加备注: id={article_id}")
        return self.db.get_article(article_id)

    def get_history(self, article_id: int) -> dict:
        article = self.db.get_article(article_id)
        if not article:
            raise ValueError(f"文章不存在: id={article_id}")

        return {
            "id": article.id,
            "title": article.title,
            "status": article.status.value,
            "reviewer": article.reviewer_name,
            "review_notes": article.review_notes,
            "created_at": article.created_at.isoformat(),
            "updated_at": article.updated_at.isoformat(),
            "published_at": article.published_at.isoformat() if article.published_at else None,
        }
