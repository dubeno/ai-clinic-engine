import time
from pathlib import Path

from loguru import logger

from .config import config

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class LLMClient:
    def __init__(self):
        self.backend = config.LLM_BACKEND

        if self.backend == "anthropic":
            import anthropic
            self.client = anthropic.Anthropic(
                base_url=config.ANTHROPIC_BASE_URL,
                api_key=config.ANTHROPIC_AUTH_TOKEN,
            )
            self.model = config.ANTHROPIC_MODEL
        else:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=config.OPENAI_API_KEY,
                base_url=config.OPENAI_BASE_URL,
            )
            self.model = config.OPENAI_MODEL

    def chat(self, messages: list[dict], max_tokens: int = 4096, temperature: float = 0.7) -> str:
        if self.backend == "anthropic":
            return self._chat_anthropic(messages, max_tokens, temperature)
        else:
            return self._chat_openai(messages, max_tokens, temperature)

    def _chat_openai(self, messages: list[dict], max_tokens: int, temperature: float) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=messages,
            temperature=temperature,
            stream=False,
        )
        return completion.choices[0].message.content

    def _chat_anthropic(self, messages: list[dict], max_tokens: int, temperature: float) -> str:
        # Split system message from user/assistant messages
        system_msg = None
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                chat_messages.append(msg)

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": chat_messages,
        }
        if system_msg:
            kwargs["system"] = system_msg

        response = self.client.messages.create(**kwargs)
        # Extract text from response (may contain ThinkingBlock + TextBlock)
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""

    def chat_with_system(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.chat(messages, **kwargs)

    def chat_from_template(self, template_name: str, max_tokens: int = 4096, temperature: float = 0.7, **variables) -> str:
        template_path = TEMPLATES_DIR / f"{template_name}.txt"
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        template = template_path.read_text(encoding="utf-8")

        for key, value in variables.items():
            template = template.replace(f"{{{key}}}", str(value))

        if "---" in template:
            parts = template.split("---", 1)
            system_msg = parts[0].strip()
            user_msg = parts[1].strip()
        else:
            system_msg = "你是一位专业的医疗健康内容写手。"
            user_msg = template

        return self.chat_with_system(system_msg, user_msg, max_tokens=max_tokens, temperature=temperature)

    def chat_with_retry(self, messages: list[dict], max_retries: int = 3, **kwargs) -> str:
        for attempt in range(max_retries):
            try:
                return self.chat(messages, **kwargs)
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    logger.warning(f"LLM call failed (attempt {attempt + 1}), retrying in {wait}s: {e}")
                    time.sleep(wait)
                else:
                    raise
