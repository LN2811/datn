import logging
import time
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from openai import APIError, OpenAI, RateLimitError

from app.services.ai_context_guard import require_context_selection

logger = logging.getLogger("uvicorn.error")
RATE_LIMIT_BACKOFF_SECONDS = (10, 30, 60)


class AIProviderRateLimitError(HTTPException):
    def __init__(self, *, provider: str, model: str, error_code: str):
        self.provider = provider
        self.model = model
        self.error_code = error_code
        super().__init__(
            status_code=429,
            detail={
                "message": "AI provider is busy. Retry later.",
                "provider": provider,
                "model": model,
                "error_code": error_code,
            },
        )


@dataclass
class AIProviderClient:
    provider: str
    api_key: str
    base_url: str
    model: str


@dataclass
class AIProviderResponse:
    content: str
    tokens_used: int | None = None
    model_name: str | None = None
    provider: str | None = None


class AIProviderService:
    @staticmethod
    def _rate_limit_error_code(exc: RateLimitError) -> str:
        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            error = body.get("error")
            if isinstance(error, dict):
                return str(error.get("code") or error.get("type") or "rate_limit")
        return "rate_limit"

    @staticmethod
    def chat(
        config: AIProviderClient,
        messages: list[dict[str, Any]],
        response_format: dict[str, Any] | None = None,
        temperature: float = 0.2,
        max_completion_tokens: int | None = None,
        context_selection: Any = None,
    ) -> AIProviderResponse:
        require_context_selection(context_selection)
        if not config.api_key:
            raise HTTPException(status_code=400, detail="AI provider API key is not configured.")

        client = OpenAI(api_key=config.api_key, base_url=config.base_url)

        for request_attempt in range(len(RATE_LIMIT_BACKOFF_SECONDS) + 1):
            try:
                payload: dict[str, Any] = {
                    "model": config.model,
                    "messages": messages,
                    "temperature": temperature,
                }

                if response_format:
                    payload["response_format"] = response_format

                if max_completion_tokens is not None:
                    payload["max_completion_tokens"] = max_completion_tokens

                response = client.chat.completions.create(**payload)
                tokens_used = response.usage.total_tokens if response.usage else None

                return AIProviderResponse(
                    content=response.choices[0].message.content or "{}",
                    tokens_used=tokens_used,
                    model_name=response.model,
                    provider=config.provider,
                )
            except RateLimitError as exc:
                error_code = AIProviderService._rate_limit_error_code(exc)
                if request_attempt >= len(RATE_LIMIT_BACKOFF_SECONDS):
                    logger.warning(
                        "AI provider rate limit retries exhausted. provider=%s "
                        "model=%s attempt=%s wait_seconds=0 error_code=%s",
                        config.provider,
                        config.model,
                        request_attempt + 1,
                        error_code,
                    )
                    raise AIProviderRateLimitError(
                        provider=config.provider,
                        model=config.model,
                        error_code=error_code,
                    ) from exc
                wait_seconds = RATE_LIMIT_BACKOFF_SECONDS[request_attempt]
                logger.warning(
                    "AI provider rate limited. provider=%s model=%s attempt=%s "
                    "wait_seconds=%s error_code=%s",
                    config.provider,
                    config.model,
                    request_attempt + 1,
                    wait_seconds,
                    error_code,
                )
                time.sleep(wait_seconds)
            except APIError as exc:
                raise HTTPException(status_code=502, detail=f"Error from AI provider: {exc}") from exc
