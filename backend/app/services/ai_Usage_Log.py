import uuid
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, func, select

from app.models.models import AIUsageLogs
from app.services.user_subscriptions import UserSubscriptionService


class AIUsageService:

    MODEL_PRICING = {
        "gpt-4o": 0.00001,
        "gpt-4.1": 0.000008,
        "claude": 0.000009,
    }

    ACTION_LIMITS = {
        "generate_analysis": 20,
        "generate_feedback": 30,
        "generate_curriculum": 10,
    }

    def calculate_cost(self, model_name: Optional[str], tokens: int) -> float:
        safe_tokens = max(tokens, 0)
        pricing_key = model_name or "gpt-4o"
        price_per_token = self.MODEL_PRICING.get(
            pricing_key,
            self.MODEL_PRICING["gpt-4o"],
        )
        return safe_tokens * price_per_token

    def log_usage(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        project_id: Optional[uuid.UUID],
        action_type: str,
        model_name: Optional[str] = None,
        tokens_used: int,
    ):
        safe_tokens = max(tokens_used, 0)
        cost = self.calculate_cost(model_name, safe_tokens)

        log = AIUsageLogs(
            user_id=user_id,
            project_id=project_id,
            action_type=action_type,
            tokens_used=safe_tokens,
            model_name=model_name,
            cost_amount=cost,
            created_at=datetime.utcnow(),
        )

        session.add(log)
        session.commit()
        session.refresh(log)

        return log

    def get_monthly_usage(self, *, session: Session, user_id: uuid.UUID):
        now = datetime.utcnow()

        total = session.exec(
            select(
                func.coalesce(func.sum(AIUsageLogs.tokens_used), 0)
            ).where(
                AIUsageLogs.user_id == user_id,
                func.extract("year", AIUsageLogs.created_at) == now.year,
                func.extract("month", AIUsageLogs.created_at) == now.month,
            )
        ).one()

        return total or 0

    def check_quota(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        tokens_required: int = 0,
    ):
        subscription_data = UserSubscriptionService(session).check_subscription(
            user_id=user_id
        )

        remaining_tokens = subscription_data.get("remaining_tokens")
        if remaining_tokens is None:
            return

        if tokens_required > remaining_tokens:
            raise HTTPException(status_code=403, detail="Monthly AI quota exceeded")

    def check_rate_limit(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        action_type: str,
    ):
        limit = self.ACTION_LIMITS.get(action_type)
        if not limit:
            return

        today = datetime.utcnow()

        count = session.exec(
            select(func.count(AIUsageLogs.id)).where(
                AIUsageLogs.user_id == user_id,
                AIUsageLogs.action_type == action_type,
                func.extract("day", AIUsageLogs.created_at) == today.day,
                func.extract("month", AIUsageLogs.created_at) == today.month,
                func.extract("year", AIUsageLogs.created_at) == today.year,
            )
        ).one()

        if count >= limit:
            raise HTTPException(status_code=429, detail="Action rate limit exceeded")

    def admin_dashboard_stats(self, *, session: Session):
        total_tokens = session.exec(
            select(func.coalesce(func.sum(AIUsageLogs.tokens_used), 0))
        ).one()

        total_cost = session.exec(
            select(func.coalesce(func.sum(AIUsageLogs.cost_amount), 0))
        ).one()

        top_users = session.exec(
            select(
                AIUsageLogs.user_id,
                func.sum(AIUsageLogs.tokens_used).label("total"),
            )
            .group_by(AIUsageLogs.user_id)
            .order_by(func.sum(AIUsageLogs.tokens_used).desc())
            .limit(5)
        ).all()

        return {
            "total_tokens": total_tokens or 0,
            "total_cost": total_cost or 0,
            "top_users": top_users,
        }
