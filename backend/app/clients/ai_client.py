"""AI client that produces a summary + sentiment for an article.

``AIClient`` is a Protocol (capability + a ``model`` label). ``OpenAIClient``
asks the model for a single strict-JSON object, which we validate with Pydantic
so a malformed response fails loudly instead of silently corrupting data. The
underlying SDK client is created lazily, so the app boots fine without a key —
the error only surfaces when analysis is actually requested.
"""

from __future__ import annotations

import json
import logging
from typing import Protocol

from openai import AsyncOpenAI, OpenAIError

from app.config import Settings
from app.errors import AIServiceError
from app.schemas.analysis import AIResult, ArticleInput

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a precise news analyst. Given a news article, produce a concise, "
    "neutral summary and classify its overall sentiment. "
    "Respond with a JSON object ONLY, with exactly these keys: "
    '"summary" (2-3 sentence string), '
    '"sentiment" (one of "positive", "neutral", "negative"), '
    '"sentiment_score" (number from -1.0 for very negative to 1.0 for very '
    "positive, 0 for neutral). Do not include any text outside the JSON object."
)


class AIClient(Protocol):
    model: str

    async def analyze(self, article: ArticleInput) -> AIResult: ...


class OpenAIClient:
    def __init__(self, settings: Settings, client: AsyncOpenAI | None = None) -> None:
        self._settings = settings
        self.model = settings.openai_model
        self._client = client

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            if not self._settings.openai_api_key:
                raise AIServiceError(
                    "AI analysis is not configured (set OPENAI_API_KEY).",
                    status_code=503,
                )
            self._client = AsyncOpenAI(
                api_key=self._settings.openai_api_key,
                base_url=self._settings.openai_base_url,
                timeout=self._settings.openai_timeout_seconds,
                max_retries=self._settings.openai_max_retries,
            )
        return self._client

    async def aclose(self) -> None:
        # Close the underlying httpx pool the OpenAI SDK owns (no-op if unused).
        if self._client is not None:
            await self._client.close()

    async def analyze(self, article: ArticleInput) -> AIResult:
        client = self._get_client()
        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": self._build_prompt(article)},
                ],
                response_format={"type": "json_object"},
                temperature=self._settings.openai_temperature,
                max_tokens=self._settings.ai_max_output_tokens,
            )
        except OpenAIError:
            # Log the detail server-side; return a generic message to the client.
            logger.exception("OpenAI request failed")
            raise AIServiceError("The AI provider is currently unavailable.") from None

        if not response.choices:
            raise AIServiceError("The AI returned an empty response.")
        return self._parse(response.choices[0].message.content or "")

    def _build_prompt(self, article: ArticleInput) -> str:
        parts = [f"Title: {article.title}"]
        if article.source_name:
            parts.append(f"Source: {article.source_name}")
        if article.description:
            parts.append(f"Description: {article.description}")
        if article.content:
            parts.append(f"Content: {article.content}")
        return "\n".join(parts)[: self._settings.ai_max_input_chars]

    @staticmethod
    def _parse(content: str) -> AIResult:
        if not content.strip():
            raise AIServiceError("The AI returned an empty response.")
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise AIServiceError("The AI returned malformed JSON.") from exc
        try:
            return AIResult.model_validate(data)
        except ValueError as exc:
            raise AIServiceError(f"The AI response did not match the schema: {exc}") from exc
