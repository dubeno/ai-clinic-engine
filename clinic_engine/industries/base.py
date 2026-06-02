"""行业插件基类 — 定义所有行业必须实现的接口"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


@dataclass
class ComplianceRule:
    """广告法/合规规则"""
    pattern: str           # 正则表达式
    message: str           # 违规说明
    severity: str = "error"  # "error" | "warning"


@dataclass
class ClaimPattern:
    """声明提取模式"""
    category: str          # 类别: dosage, statistic, employment_rate 等
    pattern: str           # 正则表达式
    description: str = ""


class IndustryProfile(ABC):
    """行业插件接口 — 每个行业必须实现此类"""

    # ── 身份 ──

    @property
    @abstractmethod
    def industry_id(self) -> str:
        """机器可读标识，如 'medical', 'ai_career'"""

    @property
    @abstractmethod
    def industry_name(self) -> str:
        """显示名称，如 '医疗诊所', 'AI大模型求职'"""

    # ── 分类体系 ──

    @property
    @abstractmethod
    def specialty_enum(self) -> type[Enum]:
        """专科/分类枚举类"""

    @property
    @abstractmethod
    def specialty_names(self) -> dict:
        """枚举值 → 显示名称"""

    @property
    @abstractmethod
    def default_specialty(self) -> Enum:
        """默认分类"""

    # ── 合规 ──

    @property
    @abstractmethod
    def ad_law_patterns(self) -> list[ComplianceRule]:
        """广告法禁止用语"""

    @property
    @abstractmethod
    def disclaimer_patterns(self) -> list[str]:
        """免责声明检测正则"""

    @property
    @abstractmethod
    def default_disclaimer(self) -> str:
        """默认免责声明文本"""

    # ── 范围检查 ──

    def out_of_scope_terms(self, specialty_value: str) -> list[str]:
        """超出业务范围的术语列表"""
        return []

    # ── 声明提取 ──

    @property
    @abstractmethod
    def claim_patterns(self) -> list[ClaimPattern]:
        """声明提取正则模式"""

    def claim_stopwords(self) -> set[str]:
        """声明关键词提取停用词"""
        return set()

    # ── 内容生成 ──

    @property
    @abstractmethod
    def specialty_contexts(self) -> dict:
        """各分类的写作上下文"""

    @abstractmethod
    def system_prompt(self, specialty_name: str) -> str:
        """LLM 系统提示词"""

    @abstractmethod
    def writing_requirements(self) -> list[str]:
        """写作要求清单"""

    # ── 关键词 ──

    @property
    @abstractmethod
    def seed_keywords(self) -> dict:
        """各分类的种子关键词"""

    @abstractmethod
    def keyword_system_prompt(self, specialty_name: str) -> str:
        """关键词扩展的系统提示词"""

    def keyword_fallback_prefixes(self) -> list[str]:
        return ["", "怎么", "如何", "为什么"]

    def keyword_fallback_suffixes(self) -> list[str]:
        return ["", "怎么办", "的原因", "的方法"]

    # ── 知识库 ──

    @property
    @abstractmethod
    def knowledge_dir(self) -> Path:
        """知识文档目录"""

    @property
    def collection_name(self) -> str:
        """RAG 集合名称"""
        return f"{self.industry_id}_knowledge"

    # ── 品牌 ──

    @property
    def brand_name(self) -> str:
        """机构/品牌名称"""
        return ""

    @property
    def reviewer_role(self) -> str:
        """审核人角色"""
        return "审核员"
