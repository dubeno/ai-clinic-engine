"""行业插件注册表"""

from __future__ import annotations

import importlib
from functools import lru_cache

from .base import IndustryProfile

_REGISTRY: dict[str, str] = {
    "medical": "clinic_engine.industries.medical.profile.MedicalProfile",
    "ai_career": "clinic_engine.industries.ai_career.profile.AICareerProfile",
}


@lru_cache(maxsize=1)
def get_profile(industry_id: str | None = None) -> IndustryProfile:
    """加载并返回当前行业 profile"""
    if industry_id is None:
        from clinic_engine.config import config
        industry_id = config.INDUSTRY

    cls_path = _REGISTRY.get(industry_id)
    if cls_path is None:
        raise ValueError(f"未知行业: {industry_id}。可选: {list(_REGISTRY.keys())}")

    module_path, class_name = cls_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)()
