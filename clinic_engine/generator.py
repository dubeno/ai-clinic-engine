from loguru import logger

from .db import Database
from .industries import get_profile
from .llm import LLMClient
from .models import (
    Article,
    ArticleStatus,
    ContentType,
    Topic,
    CONTENT_TYPE_NAMES,
)

try:
    from .rag import KnowledgeBase
    HAS_RAG = True
except ImportError:
    HAS_RAG = False


class ContentGenerator(LLMClient):
    def __init__(self, db: Database | None = None):
        super().__init__()
        self.db = db or Database()
        self.profile = get_profile()
        self.kb = None
        if HAS_RAG:
            try:
                self.kb = KnowledgeBase()
            except Exception as e:
                logger.warning(f"知识库初始化失败，将不使用RAG: {e}")

    def generate_article(
        self,
        topic: Topic,
        content_type: ContentType | None = None,
    ) -> Article:
        content_type = content_type or topic.content_type

        # 获取专科名称
        specialty_name = self.profile.specialty_names.get(
            topic.specialty,
            topic.specialty
        )
        type_name = CONTENT_TYPE_NAMES.get(content_type, content_type.value)
        specialty_ctx = self.profile.specialty_contexts.get(
            topic.specialty,
            ""
        )

        logger.info(f"生成文章: 关键词={topic.keyword}, 类型={type_name}, 专科={specialty_name}")

        # RAG: retrieve relevant knowledge
        rag_context = ""
        if self.kb and self.kb.count() > 0:
            query = f"{topic.keyword} {' '.join(topic.related_keywords)}"
            rag_context = self.kb.get_context(query, n_results=3)
            if rag_context:
                logger.info(f"RAG 检索到 {rag_context.count('---') + 1} 条相关知识")

        word_counts = {
            ContentType.SEO_ARTICLE: "2000-3000字",
            ContentType.WECHAT: "1200-2000字",
            ContentType.XIAOHONGSHU: "500-800字",
        }
        word_count = word_counts.get(content_type, "1500-2500字")

        disclaimer = self.profile.default_disclaimer
        system = self.profile.system_prompt(specialty_name)
        requirements = self.profile.writing_requirements()

        rag_section = ""
        if rag_context:
            rag_section = f"""
以下是从参考文献中检索到的相关知识，请优先参考这些经过验证的内容：
{rag_context}

"""

        req_lines = "\n".join(f"{i+1}. {r}" for i, r in enumerate(requirements))

        user = f"""请根据以下关键词撰写一篇{type_name}。

关键词：{topic.keyword}
相关关键词：{', '.join(topic.related_keywords) if topic.related_keywords else '无'}
目标字数：{word_count}

{specialty_ctx}

{rag_section}写作要求：
{req_lines}

输出格式：
第一行：标题
空一行
正文内容

最后务必附上免责声明：{disclaimer}"""

        content = self.chat_with_system(system, user, max_tokens=4096, temperature=0.7)

        # Parse title and content
        lines = content.strip().split("\n")
        title = lines[0].strip("# ").strip() if lines else topic.keyword
        body = "\n".join(lines[1:]).strip()

        # Ensure disclaimer is present
        if disclaimer not in body:
            body = f"{body}\n\n{disclaimer}"

        article = Article(
            topic_id=topic.id,
            title=title,
            content=body,
            content_type=content_type,
            specialty=topic.specialty,
            status=ArticleStatus.DRAFT,
        )

        article_id = self.db.insert_article(article)
        article.id = article_id

        # Update topic status
        if topic.id:
            self.db.update_topic_status(topic.id, "in_progress")

        logger.success(f"文章已生成: id={article_id}, 标题={title}")
        return article

    def generate_batch(
        self,
        specialty: str = "general",
        content_type: str | ContentType = ContentType.SEO_ARTICLE,
        limit: int = 3,
    ) -> list[Article]:
        topics = self.db.get_pending_topics(limit=limit)
        if not topics:
            logger.warning("没有待处理的关键词，请先运行 keyword research")
            return []

        articles = []
        for topic in topics:
            try:
                article = self.generate_article(topic, ContentType(content_type) if isinstance(content_type, str) else content_type)
                articles.append(article)
            except Exception as e:
                logger.error(f"生成文章失败: topic={topic.keyword}, error={e}")
        return articles
