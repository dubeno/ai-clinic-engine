"""医疗诊所行业 Profile"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from clinic_engine.industries.base import ClaimPattern, ComplianceRule, IndustryProfile


class MedicalSpecialty(str, Enum):
    TCM = "traditional_chinese_medicine"
    DENTAL = "dental"
    DERMATOLOGY = "dermatology"
    GYNECOLOGY = "gynecology"
    GENERAL = "general"


class MedicalProfile(IndustryProfile):
    industry_id = "medical"
    industry_name = "医疗诊所"

    specialty_enum = MedicalSpecialty
    specialty_names = {
        MedicalSpecialty.TCM: "中医",
        MedicalSpecialty.DENTAL: "口腔",
        MedicalSpecialty.DERMATOLOGY: "皮肤科",
        MedicalSpecialty.GYNECOLOGY: "妇产科",
        MedicalSpecialty.GENERAL: "全科",
    }
    default_specialty = MedicalSpecialty.GENERAL

    # 合规
    ad_law_patterns = [
        ComplianceRule(r"100%.*(?:有效|治愈|成功)", "广告法禁止使用绝对化保证"),
        ComplianceRule(r"根治|包治|药到病除", "广告法禁止承诺治愈效果"),
        ComplianceRule(r"(?:最好|最佳|第一|唯一|顶级|极致)", "广告法禁止使用极限用语"),
        ComplianceRule(r"无副作用|零副作用|没有任何副作用", "广告法禁止承诺无副作用"),
        ComplianceRule(r"永不复发|终身不犯", "广告法禁止承诺长期效果"),
        ComplianceRule(r"祖传秘方|宫廷秘方", "禁止使用未经验证的秘方宣传"),
        ComplianceRule(r"治愈率\s*\d+%", "禁止宣传具体治愈率"),
        ComplianceRule(r"安全无痛|绝对安全", "禁止使用绝对化安全承诺"),
        ComplianceRule(r"立竿见影|一次见效|即刻见效", "禁止承诺即时效果"),
    ]

    disclaimer_patterns = [
        r"仅供参考",
        r"不构成医疗建议",
        r"不构成诊疗建议",
        r"请咨询专业医生",
        r"请遵医嘱",
    ]

    default_disclaimer = "本文仅供参考，不构成医疗建议。如有健康问题，请咨询专业医生。"

    # 范围
    _out_of_scope = {
        "dental": ["心脏手术", "脑外科", "骨科手术"],
        "dermatology": ["牙科", "种植牙", "正畸"],
        "gynecology": ["骨科", "牙科", "眼科"],
        "traditional_chinese_medicine": ["西医手术", "化疗方案", "放疗"],
    }

    def out_of_scope_terms(self, specialty_value: str) -> list[str]:
        return self._out_of_scope.get(specialty_value, [])

    # 声明
    claim_patterns = [
        ClaimPattern("dosage", r"(\d+\.?\d*)\s*(mg|毫克|g|克|ml|毫升|μg|微克)"),
        ClaimPattern("statistic", r"(\d+\.?\d*)\s*(%|倍|天|周|个月|年|次)"),
        ClaimPattern("recommendation", r"(建议|推荐|应当|需要|应该|指南|专家共识)"),
        ClaimPattern("contraindication", r"(禁忌|禁止|不可|不能|不宜|避免|慎用|禁用)"),
        ClaimPattern("diagnosis", r"(诊断|确诊|检查|筛查|检测|阳性|阴性)"),
    ]

    # 内容生成
    specialty_contexts = {
        MedicalSpecialty.TCM: "文章中适当引用中医经典理论和概念，如阴阳平衡、五行学说、经络理论等。可引用《黄帝内经》《伤寒论》等经典古籍。",
        MedicalSpecialty.DENTAL: "关注口腔健康日常护理，强调定期检查的重要性。涉及治疗方案时请标注需医生评估。",
        MedicalSpecialty.DERMATOLOGY: "注重皮肤护理的科学性，区分医学护肤和日常护肤。避免推荐具体品牌产品。",
        MedicalSpecialty.GYNECOLOGY: "关注女性全生命周期健康管理。涉及生育、孕期等敏感话题时需格外谨慎用词。",
        MedicalSpecialty.GENERAL: "面向普通患者，语言通俗易懂，避免过于专业的医学术语，必要时给出通俗解释。",
    }

    def system_prompt(self, specialty_name: str) -> str:
        return (
            f"你是一位专业的{specialty_name}医疗健康内容写手。"
            "你的文章基于循证医学，语言专业但通俗易懂，面向患者和普通读者。"
            "你需要确保内容的医学准确性，任何不确定的医学观点请标注'需医生确认'。"
        )

    def writing_requirements(self) -> list[str]:
        return [
            "标题要吸引人且包含关键词",
            "内容要有清晰的结构（使用H2/H3小标题）",
            "语言专业但通俗易懂，面向患者读者",
            "包含实用的健康建议",
            "如果参考了上述知识库内容，请标注具体来源（如\"来源：《XX指南》\"）",
            "每个重要医学观点需标注来源或注明'需医生确认'",
            "不要使用绝对化用语（如\"100%有效\"、\"根治\"、\"最好\"等）",
            "结尾加入就医引导",
        ]

    # 关键词
    seed_keywords = {
        MedicalSpecialty.TCM: ["中医调理", "针灸", "中药方剂", "中医养生", "体质辨识"],
        MedicalSpecialty.DENTAL: ["种植牙", "正畸", "洗牙", "智齿", "烤瓷牙"],
        MedicalSpecialty.DERMATOLOGY: ["湿疹", "痤疮", "祛斑", "过敏性皮炎", "脱发"],
        MedicalSpecialty.GYNECOLOGY: ["多囊卵巢", "月经不调", "备孕", "妇科检查", "更年期"],
        MedicalSpecialty.GENERAL: ["体检", "慢性病管理", "高血压", "糖尿病", "亚健康"],
    }

    def keyword_system_prompt(self, specialty_name: str) -> str:
        return (
            f"你是一位{specialty_name}领域的医疗SEO专家。"
            "根据给定的种子关键词，生成患者在搜索引擎上常搜索的关键词列表。"
        )

    def keyword_fallback_prefixes(self) -> list[str]:
        return ["", "怎么", "如何", "为什么", "多少钱", "疼不疼", "注意事项", "能治好吗", "吃什么好"]

    def keyword_fallback_suffixes(self) -> list[str]:
        return ["", "怎么办", "的原因", "的治疗方法", "的预防", "症状", "检查"]

    # 知识库
    knowledge_dir = Path(__file__).parent / "knowledge"

    # 品牌
    brand_name = "示例诊所"
    reviewer_role = "医生"
