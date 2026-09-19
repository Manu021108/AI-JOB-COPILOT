from typing import Protocol
import httpx
from app.core.config import get_settings


class LLMError(Exception):
    pass


class LLMProvider(Protocol):
    name: str

    def complete(self, system_prompt: str, user_prompt: str) -> str: ...


class OpenAICompatibleProvider:
    """Minimal OpenAI-compatible chat completions client (httpx-based)."""

    name = "openai-compatible"

    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.base_url}/chat/completions"
        try:
            response = httpx.post(
                url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0,
                },
                timeout=120,
            )
        except httpx.HTTPError as exc:
            raise LLMError(f"Could not reach the LLM provider: {exc}") from exc
        if response.status_code != 200:
            raise LLMError(f"LLM provider returned HTTP {response.status_code}")
        try:
            return response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            raise LLMError("LLM provider returned an unexpected response.") from exc


class MockLLMProvider:
    """Deterministic, offline provider used for development and automated tests.

    Extracts structured data from resume text using heuristics. Never makes a
    network call, so it is safe for CI and for local runs without an API key.
    """

    name = "mock"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if "JOB DESCRIPTION:" in (user_prompt or "") and "```" in (user_prompt or ""):
            from app.ai.mock_job_extractor import extract_from_text as extract_job

            return extract_job(_extract_prompts_resume_text(user_prompt, marker="JOB DESCRIPTION:"))
        from app.ai.mock_extractor import extract_from_text

        return extract_from_text(_extract_resume_text(user_prompt))


def _extract_resume_text(user_prompt: str) -> str:
    return _extract_prompts_resume_text(user_prompt, marker="RESUME TEXT:")


def _extract_prompts_resume_text(user_prompt: str, marker: str) -> str:
    import re

    match = re.search(rf"{re.escape(marker)}\s*\n*```(.*?)```", user_prompt, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return user_prompt


def build_provider() -> LLMProvider:
    settings = get_settings()
    chosen = (settings.llm_provider or "mock").strip().lower()
    if chosen == "openai" and settings.llm_api_key:
        return OpenAICompatibleProvider(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            base_url=settings.llm_base_url,
        )
    return MockLLMProvider()