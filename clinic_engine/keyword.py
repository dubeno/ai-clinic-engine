import json
import random

from loguru import logger

from .db import Database
from .industries import get_profile
from .llm import LLMClient
from .models import ContentType, Topic


class KeywordEngine(LLMClient):
    def __init__(self, db: Database | None = None):
        super().__init__()
        self.db = db or Database()
        self.profile = get_profile()

    def research(
        self,
        specialty: str = None,
        seed: str | None = None,
        content_type: str | ContentType = ContentType.SEO_ARTICLE,
        limit: int = 20,
    ) -> list[Topic]:
        if specialty is None:
            specialty = self.profile.default_specialty.value

        content_type_enum = ContentType(content_type) if isinstance(content_type, str) else content_type

        # 获取专科名称
        specialty_name = self.profile.specialty_names.get(
            specialty,
            specialty
        )

        if not seed:
            seeds = self.profile.seed_keywords.get(specialty, self.profile.seed_keywords.get(self.profile.default_specialty, ["通用"]))
            seed = random.choice(seeds)

        logger.info(f"关键词研究: 专科={specialty_name}, 种子词={seed}, 目标数={limit}")

        # Step 1: Expand keywords with LLM
        keywords = self._expand_keywords(seed, specialty_name, limit)
        logger.info(f"LLM 扩展得到 {len(keywords)} 个关键词")

        # Step 2: Score each keyword
        topics: list[Topic] = []
        for kw_data in keywords[:limit]:
            keyword = kw_data["keyword"]
            volume = kw_data.get("search_volume", random.randint(100, 5000))
            competition = kw_data.get("competition", round(random.uniform(0.2, 0.8), 2))
            relevance = kw_data.get("relevance", round(random.uniform(0.6, 1.0), 2))
            priority = round(volume * relevance * (1 - competition), 2)

            topic = Topic(
                keyword=keyword,
                search_volume=volume,
                competition=competition,
                relevance_score=relevance,
                related_keywords=kw_data.get("related_keywords", []),
                content_type=content_type_enum,
                specialty=specialty,
                priority_score=priority,
            )
            topic_id = self.db.insert_topic(topic)
            topic.id = topic_id
            topics.append(topic)

        logger.success(f"已插入 {len(topics)} 个关键词到数据库")
        return topics

    def _expand_keywords(self, seed: str, specialty_name: str, limit: int) -> list[dict]:
        system = self.profile.keyword_system_prompt(specialty_name)
        user = f"""种子关键词：{seed}
专科领域：{specialty_name}
请生成 {limit} 个相关的搜索关键词。

返回格式为 JSON 数组，每个元素包含：
- keyword: 搜索关键词（口语化，像真实用户会搜的）
- search_volume: 估计月搜索量（整数，100-10000之间）
- competition: 竞争程度（0.0-1.0）
- relevance: 与{specialty_name}的相关度（0.0-1.0）
- related_keywords: 2-3个相关关键词列表

只返回 JSON，不要其他内容。"""

        try:
            response = self.chat_with_system(system, user, temperature=0.8)
            response = response.strip()
            if response.startswith("```"):
                response = response.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(response)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"LLM关键词扩展失败，使用回退方案: {e}")
            return self._fallback_keywords(seed, limit)

    def _fallback_keywords(self, seed: str, limit: int) -> list[dict]:
        prefixes = self.profile.keyword_fallback_prefixes()
        suffixes = self.profile.keyword_fallback_suffixes()
        results = []
        for p in prefixes[:limit]:
            for s in suffixes[:2]:
                if len(results) >= limit:
                    break
                kw = f"{p}{seed}{s}"
                if kw != seed:
                    results.append({
                        "keyword": kw,
                        "search_volume": random.randint(200, 3000),
                        "competition": round(random.uniform(0.3, 0.7), 2),
                        "relevance": 0.9,
                        "related_keywords": [],
                    })
        return results[:limit]

    def list_topics(self, status: str | None = None, limit: int = 50) -> list[Topic]:
        return self.db.list_topics(status=status, limit=limit)
