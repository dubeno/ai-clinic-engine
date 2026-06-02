import json
import sqlite3
from datetime import datetime
from typing import Optional

from .config import config
from .models import (
    Article,
    ArticleAnalytics,
    ArticleStatus,
    ContentType,
    QualityResult,
    Topic,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    search_volume INTEGER DEFAULT 0,
    competition REAL DEFAULT 0.0,
    relevance_score REAL DEFAULT 0.0,
    related_keywords TEXT DEFAULT '[]',
    content_type TEXT DEFAULT 'seo_article',
    specialty TEXT DEFAULT 'general',
    priority_score REAL DEFAULT 0.0,
    status TEXT DEFAULT 'queued',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER REFERENCES topics(id),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    html_content TEXT,
    content_type TEXT DEFAULT 'seo_article',
    specialty TEXT DEFAULT 'general',
    status TEXT DEFAULT 'draft',
    quality_result TEXT,
    review_notes TEXT,
    reviewer_name TEXT,
    published_at TEXT,
    published_url TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER REFERENCES articles(id),
    platform TEXT NOT NULL,
    views INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    published_at TEXT,
    last_updated TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_topics_status ON topics(status);
CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);
CREATE INDEX IF NOT EXISTS idx_articles_topic ON articles(topic_id);
"""


class Database:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.DB_PATH
        self._mem_conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        if self.db_path == ":memory:":
            if self._mem_conn is None:
                self._mem_conn = sqlite3.connect(":memory:")
                self._mem_conn.row_factory = sqlite3.Row
            return self._mem_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._conn()
        conn.executescript(SCHEMA)
        if self.db_path != ":memory:":
            conn.close()

    # ── Topics ──

    def insert_topic(self, topic: Topic) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO topics
                   (keyword, search_volume, competition, relevance_score,
                    related_keywords, content_type, specialty, priority_score, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    topic.keyword,
                    topic.search_volume,
                    topic.competition,
                    topic.relevance_score,
                    json.dumps(topic.related_keywords, ensure_ascii=False),
                    topic.content_type.value,
                    topic.specialty if isinstance(topic.specialty, str) else topic.specialty.value,
                    topic.priority_score,
                    topic.status,
                ),
            )
            return cur.lastrowid

    def _row_to_topic(self, row: sqlite3.Row) -> Topic:
        return Topic(
            id=row["id"],
            keyword=row["keyword"],
            search_volume=row["search_volume"],
            competition=row["competition"],
            relevance_score=row["relevance_score"],
            related_keywords=json.loads(row["related_keywords"]),
            content_type=ContentType(row["content_type"]),
            specialty=row["specialty"],
            priority_score=row["priority_score"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_pending_topics(self, limit: int = 10) -> list[Topic]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM topics WHERE status = 'queued' ORDER BY priority_score DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [self._row_to_topic(r) for r in rows]

    def get_topic(self, topic_id: int) -> Optional[Topic]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
            return self._row_to_topic(row) if row else None

    def update_topic_status(self, topic_id: int, status: str):
        with self._conn() as conn:
            conn.execute("UPDATE topics SET status = ? WHERE id = ?", (status, topic_id))

    def list_topics(self, status: Optional[str] = None, limit: int = 50) -> list[Topic]:
        with self._conn() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM topics WHERE status = ? ORDER BY priority_score DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM topics ORDER BY priority_score DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [self._row_to_topic(r) for r in rows]

    # ── Articles ──

    def insert_article(self, article: Article) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO articles
                   (topic_id, title, content, html_content, content_type,
                    specialty, status, quality_result, review_notes, reviewer_name,
                    published_at, published_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    article.topic_id,
                    article.title,
                    article.content,
                    article.html_content,
                    article.content_type.value,
                    article.specialty if isinstance(article.specialty, str) else article.specialty.value,
                    article.status.value,
                    json.dumps(article.quality_result.model_dump(), ensure_ascii=False, default=str)
                    if article.quality_result
                    else None,
                    article.review_notes,
                    article.reviewer_name,
                    article.published_at.isoformat() if article.published_at else None,
                    article.published_url,
                ),
            )
            return cur.lastrowid

    def _row_to_article(self, row: sqlite3.Row) -> Article:
        quality_result = None
        if row["quality_result"]:
            qr_data = json.loads(row["quality_result"])
            quality_result = QualityResult(**qr_data)

        return Article(
            id=row["id"],
            topic_id=row["topic_id"],
            title=row["title"],
            content=row["content"],
            html_content=row["html_content"],
            content_type=ContentType(row["content_type"]),
            specialty=row["specialty"],
            status=ArticleStatus(row["status"]),
            quality_result=quality_result,
            review_notes=row["review_notes"],
            reviewer_name=row["reviewer_name"],
            published_at=datetime.fromisoformat(row["published_at"]) if row["published_at"] else None,
            published_url=row["published_url"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def get_article(self, article_id: int) -> Optional[Article]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
            return self._row_to_article(row) if row else None

    def get_articles_by_status(self, status: ArticleStatus, limit: int = 50) -> list[Article]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM articles WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status.value, limit),
            ).fetchall()
            return [self._row_to_article(r) for r in rows]

    def update_article_status(
        self,
        article_id: int,
        status: ArticleStatus,
        quality_result: Optional[QualityResult] = None,
        review_notes: Optional[str] = None,
        reviewer_name: Optional[str] = None,
        published_url: Optional[str] = None,
    ):
        now = datetime.now().isoformat()
        sets = ["status = ?", "updated_at = ?"]
        vals: list = [status.value, now]

        if quality_result is not None:
            sets.append("quality_result = ?")
            vals.append(json.dumps(quality_result.model_dump(), ensure_ascii=False, default=str))
        if review_notes is not None:
            sets.append("review_notes = ?")
            vals.append(review_notes)
        if reviewer_name is not None:
            sets.append("reviewer_name = ?")
            vals.append(reviewer_name)
        if published_url is not None:
            sets.append("published_url = ?")
            vals.append(published_url)
        if status == ArticleStatus.PUBLISHED:
            sets.append("published_at = ?")
            vals.append(now)

        vals.append(article_id)
        with self._conn() as conn:
            conn.execute(f"UPDATE articles SET {', '.join(sets)} WHERE id = ?", vals)

    # ── Analytics ──

    def insert_analytics(self, analytics: ArticleAnalytics) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO analytics (article_id, platform, views, clicks, shares, published_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    analytics.article_id,
                    analytics.platform,
                    analytics.views,
                    analytics.clicks,
                    analytics.shares,
                    analytics.published_at.isoformat(),
                ),
            )
            return cur.lastrowid

    def get_analytics_summary(self) -> dict:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM articles WHERE status='published'").fetchone()[0]
            by_type = conn.execute(
                "SELECT content_type, COUNT(*) as cnt FROM articles WHERE status='published' GROUP BY content_type"
            ).fetchall()
            by_status = conn.execute(
                "SELECT status, COUNT(*) as cnt FROM articles GROUP BY status"
            ).fetchall()
            return {
                "total_published": total,
                "by_content_type": {r["content_type"]: r["cnt"] for r in by_type},
                "by_status": {r["status"]: r["cnt"] for r in by_status},
            }
