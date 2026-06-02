import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from loguru import logger

from .config import config
from .db import Database
from .industries import get_profile
from .models import Article, ArticleStatus, ContentType


class Publisher(ABC):
    @abstractmethod
    def format_content(self, article: Article) -> str:
        ...

    @abstractmethod
    def publish(self, article: Article, **kwargs) -> dict:
        ...


class FilePublisher(Publisher):
    def __init__(self, db: Database | None = None):
        self.db = db or Database()

    def format_content(self, article: Article) -> str:
        if article.content_type == ContentType.SEO_ARTICLE:
            return self._format_seo(article)
        elif article.content_type == ContentType.WECHAT:
            return self._format_wechat(article)
        elif article.content_type == ContentType.XIAOHONGSHU:
            return self._format_xiaohongshu(article)
        return article.content

    def _format_seo(self, article: Article) -> str:
        return article.content

    def _format_wechat(self, article: Article) -> str:
        content = article.content
        html = f"""<section style="margin: 16px 0; padding: 20px; font-family: -apple-system, 'Noto Sans SC', sans-serif; line-height: 1.8; color: #333;">
<h1 style="font-size: 22px; font-weight: bold; color: #2c3e50; margin-bottom: 16px;">{article.title}</h1>
"""
        # Convert markdown-like content to simple HTML
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                html += "<br>"
            elif line.startswith("## "):
                html += f'<h2 style="font-size: 18px; font-weight: bold; color: #2980b9; margin: 20px 0 10px;">{line[3:]}</h2>'
            elif line.startswith("### "):
                html += f'<h3 style="font-size: 16px; font-weight: bold; color: #27ae60; margin: 16px 0 8px;">{line[4:]}</h3>'
            else:
                html += f'<p style="margin: 8px 0;">{line}</p>'

        html += "</section>"
        return html

    def _format_xiaohongshu(self, article: Article) -> str:
        content = article.content
        # Remove markdown headers for Xiaohongshu
        lines = content.split("\n")
        cleaned = []
        for line in lines:
            line = line.strip()
            if line.startswith("#"):
                line = line.lstrip("# ").strip()
                if line:
                    cleaned.append(f"\n {line}\n")
            elif line:
                cleaned.append(line)
        return "\n".join(cleaned)

    def publish(self, article: Article, output_dir: str | None = None) -> dict:
        output_dir = output_dir or config.OUTPUT_DIR
        ext_map = {
            ContentType.SEO_ARTICLE: ".md",
            ContentType.WECHAT: ".html",
            ContentType.XIAOHONGSHU: ".txt",
        }
        ext = ext_map.get(article.content_type, ".txt")

        # Create output directory
        type_dir = Path(output_dir) / article.content_type.value
        type_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename
        safe_title = "".join(c if c.isalnum() or c in "- _" else "_" for c in article.title)
        safe_title = safe_title[:50].strip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{safe_title}{ext}"
        filepath = type_dir / filename

        formatted = self.format_content(article)
        filepath.write_text(formatted, encoding="utf-8")

        # Update article status
        if article.id:
            self.db.update_article_status(
                article.id,
                ArticleStatus.PUBLISHED,
                published_url=str(filepath),
            )

        logger.success(f"文章已发布到文件: {filepath}")
        return {"path": str(filepath), "platform": "file"}


class WeChatPublisher(Publisher):
    def __init__(self, db: Database | None = None):
        self.db = db or Database()

    def format_content(self, article: Article) -> str:
        fp = FilePublisher()
        return fp._format_wechat(article)

    def publish(self, article: Article, **kwargs) -> dict:
        try:
            from wechatpy import WeChatClient

            client = WeChatClient(config.WECHAT_APP_ID, config.WECHAT_APP_SECRET)
            html_content = self.format_content(article)

            article_data = {
                "title": article.title,
                "author": get_profile().brand_name,
                "digest": article.content[:120].replace("\n", " "),
                "content": html_content,
                "show_cover_pic": 1,
            }

            result = client.post("draft/add", data={"articles": [article_data]})
            media_id = result.get("media_id", "")

            if article.id:
                self.db.update_article_status(
                    article.id,
                    ArticleStatus.PUBLISHED,
                    published_url=f"wechat_media:{media_id}",
                )

            logger.success(f"文章已发布到微信草稿: media_id={media_id}")
            return {"media_id": media_id, "platform": "wechat"}

        except Exception as e:
            logger.error(f"微信发布失败: {e}")
            return {"error": str(e), "platform": "wechat"}
