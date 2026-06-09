import uuid
import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.core.config import settings
from app.models import AIUsageLogs, PricingPlans, UserSubscriptions
from app.services.ai_provider_client import (
    AIProviderClient,
    AIProviderRateLimitError,
    AIProviderResponse,
    AIProviderService,
)
from app.services.context_selector import ContextSelection, ContextSelector

logger = logging.getLogger("uvicorn.error")


class AITransactionService:
    @staticmethod
    def chat(
        db: Session,
        user_id: uuid.UUID,
        project_id: uuid.UUID | None,
        action_type: str,
        messages: list[dict[str, Any]],
        response_format: dict[str, Any] | None = None,
        temperature: float = 0.2,
        max_completion_tokens: int | None = None,
        context_selection: Any = None,
    )-> str:
        plan = AITransactionService._get_current_plan(db, user_id=user_id)
        AITransactionService._check_plan_limit(db, user_id=user_id, plan=plan)
        provider_config = AITransactionService._get_provider_config(plan)
        try:
            response = AIProviderService.chat(
                provider_config,
                messages,
                response_format=response_format,
                temperature=temperature,
                max_completion_tokens=max_completion_tokens,
                context_selection=context_selection,
            )
        except AIProviderRateLimitError:
            if (
                provider_config.provider == "groq"
                or not settings.PREMIUM_AI_FALLBACK_TO_GROQ_ENABLED
            ):
                raise
            response = AITransactionService._chat_with_groq_fallback(
                messages=messages,
                response_format=response_format,
                temperature=temperature,
                max_completion_tokens=max_completion_tokens,
                context_selection=context_selection,
            )
        AITransactionService._save_ai_usage_log(
            db,
            user_id=user_id,
            project_id=project_id,
            action_type=action_type,
            provider_response=response,
        )
        return response.content

    @staticmethod
    def _chat_with_groq_fallback(
        *,
        messages: list[dict[str, Any]],
        response_format: dict[str, Any] | None,
        temperature: float,
        max_completion_tokens: int | None,
        context_selection: ContextSelection,
    ) -> AIProviderResponse:
        fallback_selection = ContextSelector(session=None).trim_to_token_budget(
            context_selection,
            max_tokens=settings.GROQ_MAX_TOKENS,
            retrieval_strategy_suffix="groq_fallback_trim",
        )
        if fallback_selection.estimated_tokens > settings.GROQ_MAX_TOKENS:
            raise RuntimeError("Groq fallback rejected: context exceeds GROQ_MAX_TOKENS")
        fallback_messages = [
            {
                **message,
                "content": (
                    str(message.get("content") or "").replace(
                        context_selection.text,
                        fallback_selection.text,
                    )
                ),
            }
            for message in messages
        ]
        groq_config = AITransactionService._get_groq_config()
        logger.warning(
            "Premium AI provider unavailable. Falling back to Groq with trimmed "
            "context. provider=%s model=%s context_tokens=%s token_budget=%s",
            groq_config.provider,
            groq_config.model,
            fallback_selection.estimated_tokens,
            settings.GROQ_MAX_TOKENS,
        )
        return AIProviderService.chat(
            groq_config,
            fallback_messages,
            response_format=response_format,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
            context_selection=fallback_selection,
        )
    
    @staticmethod
    def _get_current_plan(
        db: Session, user_id: uuid.UUID
    )-> PricingPlans | None:
        now = datetime.utcnow()
        statement = (
            select(PricingPlans)
            .join(UserSubscriptions, UserSubscriptions.plan_id == PricingPlans.id)
            .where(UserSubscriptions.user_id == user_id)
            .where(
                or_(
                    UserSubscriptions.start_date <= now,
                    UserSubscriptions.start_date.is_(None),
                )
            )
            .where(
                or_(
                    UserSubscriptions.end_date >= now,
                    UserSubscriptions.end_date.is_(None),
                )
            )
            .where(PricingPlans.is_active == True)
            .order_by(PricingPlans.created_at.desc())
        )
        return db.exec(statement).first()
    
    @staticmethod
    def _check_plan_limit(
        db: Session,
        user_id: uuid.UUID,
        plan: PricingPlans | None
    )-> None:
        if plan is None:
            raise HTTPException(status_code=403, detail="No active subscription plan found.")
        limit = plan.ai_usage_limit
        if limit is None or limit <= 0:
            return

        used_tokens = AITransactionService._count_user_tokens(db, user_id)
        if used_tokens >= limit:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"AI usage limit reached for your current plan ({plan.name}). "
                    "Please upgrade your plan to continue using AI features."
                ),
            )
    @staticmethod
    def _get_provider_config(
        plan: PricingPlans |None
    )-> AIProviderClient:
        if plan is None:
            logger.info(
                "Selected AI provider. provider=groq model=%s plan_name=None "
                "has_premium_key=%s fallback_reason=no_active_plan",
                settings.GROQ_MODEL,
                bool(settings.PREMIUM_AI_API_KEY),
            )
            return AITransactionService._get_groq_config()
        plan_name = plan.name.lower()
        is_premium_plan = (
            any(keyword in plan_name for keyword in ("premium", "plus", "pro"))
            or plan.price > 0
        )
        if is_premium_plan and settings.PREMIUM_AI_API_KEY:
            provider = AIProviderClient(
                provider=settings.PREMIUM_AI_PROVIDER,
                api_key=settings.PREMIUM_AI_API_KEY,
                base_url=settings.PREMIUM_AI_BASE_URL,
                model=settings.PREMIUM_AI_MODEL,
            )
            logger.info(
                "Selected AI provider. provider=%s model=%s plan_name=%s "
                "has_premium_key=%s",
                provider.provider,
                provider.model,
                plan.name,
                bool(settings.PREMIUM_AI_API_KEY),
            )
            return provider
        provider = AITransactionService._get_groq_config()
        logger.info(
            "Selected AI provider. provider=%s model=%s plan_name=%s "
            "has_premium_key=%s fallback_reason=%s",
            provider.provider,
            provider.model,
            plan.name,
            bool(settings.PREMIUM_AI_API_KEY),
            "premium_key_missing" if is_premium_plan else "non_premium_plan",
        )
        return provider
    
    @staticmethod
    def _get_groq_config() -> AIProviderClient:
        if not settings.GROQ_API_KEY:
            raise HTTPException(status_code=400, detail="GROQ API key is not configured.")
        return AIProviderClient(
            provider="groq",
            api_key=settings.GROQ_API_KEY,
            base_url=settings.GROQ_BASE_URL,
            model=settings.GROQ_MODEL,
        )

    @staticmethod
    def _count_user_tokens(
        db: Session,
        user_id: uuid.UUID
    ) -> int:
        last_24h = datetime.utcnow() - timedelta(hours=24)
        statement =(
            select(func.coalesce(func.sum(AIUsageLogs.tokens_used), 0))
            .where(AIUsageLogs.user_id == user_id)
            .where(AIUsageLogs.created_at >= last_24h)
        )
        result = db.exec(statement).one()
        return int(result or 0)
    
    @staticmethod
    def _save_ai_usage_log(
        db: Session,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        action_type: str,
        provider_response: AIProviderResponse
    )-> None:
        log_entry = AIUsageLogs(
            user_id=user_id,
            project_id=project_id,
            action_type=action_type,
            model_name=provider_response.model_name,
            tokens_used=provider_response.tokens_used
        )
        db.add(log_entry)
        db.commit()
