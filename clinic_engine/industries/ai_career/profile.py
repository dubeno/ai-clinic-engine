"""AI大模型求职行业 Profile"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from clinic_engine.industries.base import ClaimPattern, ComplianceRule, IndustryProfile


class AICareerCategory(str, Enum):
    INTERVIEW_PREP = "interview_prep"
    RESUME_OPTIMIZATION = "resume_optimization"
    TECH_DEEP_DIVE = "tech_deep_dive"
    INDUSTRY_TRENDS = "industry_trends"
    CAREER_PLANNING = "career_planning"


class AICareerProfile(IndustryProfile):
    industry_id = "ai_career"
    industry_name = "AI大模型求职"

    specialty_enum = AICareerCategory
    specialty_names = {
        AICareerCategory.INTERVIEW_PREP: "面试准备",
        AICareerCategory.RESUME_OPTIMIZATION: "简历优化",
        AICareerCategory.TECH_DEEP_DIVE: "技术深度",
        AICareerCategory.INDUSTRY_TRENDS: "行业动态",
        AICareerCategory.CAREER_PLANNING: "职业规划",
    }
    default_specialty = AICareerCategory.INTERVIEW_PREP

    # 合规
    ad_law_patterns = [
        ComplianceRule(r"保证就业|包就业|100%就业", "禁止承诺就业保障"),
        ComplianceRule(r"100%通过|包过|必过", "禁止承诺考试/面试通过"),
        ComplianceRule(r"薪资翻倍|保底薪资|guaranteed\s+.*薪", "禁止承诺薪资结果"),
        ComplianceRule(r"(?:最好|最佳|第一|唯一|顶级|极致)", "广告法禁止使用极限用语"),
        ComplianceRule(r"保offer|guaranteed\s+offer", "禁止承诺offer保障"),
        ComplianceRule(r"百分之百|百分百|100%", "禁止使用绝对化保证"),
    ]

    disclaimer_patterns = [
        r"培训效果因人而异",
        r"不保证就业结果",
        r"仅供参考",
        r"具体情况因人而异",
    ]

    default_disclaimer = "培训效果因人而异，本文内容仅供参考，不保证就业结果。"

    # 范围
    def out_of_scope_terms(self, specialty_value: str) -> list[str]:
        scope = {
            "interview_prep": ["医疗诊断", "法律咨询", "财务投资建议"],
            "resume_optimization": ["医疗处方", "法律意见"],
            "tech_deep_dive": ["医疗手术", "心理咨询"],
        }
        return scope.get(specialty_value, [])

    # 声明
    claim_patterns = [
        ClaimPattern("employment_rate", r"(?:就业率|入职率|offer率)\s*(?:达|为|高达)?\s*\d+\s*%"),
        ClaimPattern("salary_stat", r"(?:薪资涨幅|薪资提升|平均薪资)\s*(?:达|为|高达)?\s*\d+"),
        ClaimPattern("pass_rate", r"(?:面试通过率|通过率)\s*(?:达|为|高达)?\s*\d+\s*%"),
        ClaimPattern("partner_company", r"(?:合作企业|合作公司|内推企业)\s*(?:包括|有|达)"),
        ClaimPattern("statistic", r"\d+\s*(%|倍|天|周|个月|年|次|人)"),
        ClaimPattern("recommendation", r"(?:建议|推荐|应当|需要|应该|指南|专家)"),
    ]

    def claim_stopwords(self) -> set[str]:
        return {"的", "了", "在", "是", "和", "与", "或", "及", "对", "为",
                "从", "到", "被", "把", "给", "让", "向", "以", "而", "但",
                "因为", "所以", "如果", "虽然", "可以", "能够", "需要", "应该",
                "建议", "推荐", "应当", "可能", "不会", "没有", "是否",
                "一个", "这些", "那些", "我们", "大家", "同学"}

    # 内容生成
    specialty_contexts = {
        AICareerCategory.INTERVIEW_PREP: (
            "关注常见面试问题和答题策略，提供模拟面试场景。"
            "内容应包含具体的技术问题示例和参考答案。"
        ),
        AICareerCategory.RESUME_OPTIMIZATION: (
            "聚焦AI/LLM岗位的简历亮点打造，强调项目经验的STAR法则描述。"
            "避免千篇一律的模板化建议。"
        ),
        AICareerCategory.TECH_DEEP_DIVE: (
            "深入讲解大模型核心技术概念（Transformer、RLHF、RAG、Fine-tuning等）。"
            "内容要有技术深度但保持可读性，适当使用类比。"
        ),
        AICareerCategory.INDUSTRY_TRENDS: (
            "关注AI行业最新动态，包括大模型公司、开源项目、论文突破等。"
            "数据和事实需要注明来源或标注时效性。"
        ),
        AICareerCategory.CAREER_PLANNING: (
            "提供AI领域的职业发展路径分析，从初级工程师到架构师/研究员的成长路线。"
            "避免过度承诺具体薪资数字。"
        ),
    }

    def system_prompt(self, specialty_name: str) -> str:
        return (
            f"你是一位专注于{specialty_name}领域的AI行业内容写手。"
            "你的文章基于行业实践和技术理解，语言专业但通俗易懂，面向AI从业者和求职者。"
            "你需要确保内容的准确性，任何不确定的观点请标注'仅供参考'。"
            "避免做出就业保障或薪资承诺。"
        )

    def writing_requirements(self) -> list[str]:
        return [
            "标题要吸引人且包含关键词",
            "内容要有清晰的结构（使用H2/H3小标题）",
            "语言专业但通俗易懂，面向AI从业者和求职者",
            "包含实用的行动建议",
            "如果参考了知识库内容，请标注具体来源",
            "技术观点需标注来源或注明'仅供参考'",
            "不要使用绝对化用语（如'保证就业'、'100%通过'、'最好'等）",
            "不要承诺具体就业率或薪资数字",
            "结尾加入引导关注或咨询",
        ]

    # 关键词
    seed_keywords = {
        AICareerCategory.INTERVIEW_PREP: [
            "大模型面试", "LLM面试题", "AI算法面试", "transformer面试",
            "深度学习面试"
        ],
        AICareerCategory.RESUME_OPTIMIZATION: [
            "AI简历", "大模型项目经验", "算法工程师简历", "LLM项目描述"
        ],
        AICareerCategory.TECH_DEEP_DIVE: [
            "RLHF原理", "RAG架构", "大模型微调", "transformer详解",
            "prompt engineering"
        ],
        AICareerCategory.INDUSTRY_TRENDS: [
            "大模型行业趋势", "AI就业市场", "LLM开源模型", "AI公司招聘"
        ],
        AICareerCategory.CAREER_PLANNING: [
            "AI职业路径", "算法工程师成长", "大模型岗位发展", "AI转行指南"
        ],
    }

    def keyword_system_prompt(self, specialty_name: str) -> str:
        return (
            f"你是一位{specialty_name}领域的AI内容SEO专家。"
            "根据给定的种子关键词，生成求职者和从业者在搜索引擎上常搜索的关键词列表。"
        )

    def keyword_fallback_prefixes(self) -> list[str]:
        return ["", "怎么", "如何", "什么是", "为什么", "2026年", "最新"]

    def keyword_fallback_suffixes(self) -> list[str]:
        return ["", "怎么办", "教程", "指南", "面试题", "入门", "进阶"]

    # 知识库
    knowledge_dir = Path(__file__).parent / "knowledge"

    # 品牌
    brand_name = "AI大模型求职训练营"
    reviewer_role = "导师"
