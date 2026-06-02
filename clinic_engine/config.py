import os
import dotenv
from loguru import logger

dotenv.load_dotenv()


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


class ClinicConfig:
    # Industry: "medical", "ai_career", etc.
    INDUSTRY: str = _env("INDUSTRY", "medical")

    # LLM backend: "openai" or "anthropic"
    LLM_BACKEND: str = _env("LLM_BACKEND", "openai")

    # OpenAI / compatible
    OPENAI_API_KEY: str = _env("OPENAI_API_KEY")
    OPENAI_BASE_URL: str = _env("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = _env("OPENAI_MODEL", "gpt-4o")

    # Anthropic / compatible
    ANTHROPIC_BASE_URL: str = _env("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    ANTHROPIC_AUTH_TOKEN: str = _env("ANTHROPIC_AUTH_TOKEN", _env("ANTHROPIC_API_KEY"))
    ANTHROPIC_MODEL: str = _env("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    # Clinic profile
    CLINIC_NAME: str = _env("CLINIC_NAME", "示例诊所")
    CLINIC_SPECIALTY: str = _env("CLINIC_SPECIALTY", "general")
    DEFAULT_DISCLAIMER: str = _env(
        "DEFAULT_DISCLAIMER",
        "本文仅供参考，不构成医疗建议。如有健康问题，请咨询专业医生。",
    )

    # SerpAPI
    SERPAPI_KEY: str = _env("SERPAPI_KEY")

    # WeChat
    WECHAT_APP_ID: str = _env("WECHAT_APP_ID")
    WECHAT_APP_SECRET: str = _env("WECHAT_APP_SECRET")

    # Database
    DB_PATH: str = _env("DB_PATH", "clinic_engine.db")

    # Output
    OUTPUT_DIR: str = _env("OUTPUT_DIR", "./output")


config = ClinicConfig()
