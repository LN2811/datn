import uuid
from datetime import datetime, timedelta
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
            "total_tokens": int(total_tokens or 0),
            "total_cost": float(total_cost or 0),
            "top_users": [
                {
                    "user_id": str(user_id),
                    "total": int(total or 0),
                }
                for user_id, total in top_users
            ],
        }
    
    def  get_24h_usage(
            self,
            *,
            session: Session,
            user_id: uuid.UUID
    ):
        last_24h = datetime.utcnow() - timedelta(hours=24)
        total = session.exec(
            select(func.coalesce(func.sum(AIUsageLogs.tokens_used),0))
            .where(AIUsageLogs.user_id == user_id)
            .where(AIUsageLogs.created_at >= last_24h)
        ).one()
        return int(total or 0)
    
    def get_quota_status(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
    ):
        used_tokens = self.get_24h_usage(
            session=session,
            user_id=user_id
        )

        try:
            subscription_data = UserSubscriptionService(session).check_subscription(
                user_id=user_id
            )
            token_limit = subscription_data.get("ai_usage_limit")
            plan_name = subscription_data.get("plan_name")
        except HTTPException:
            token_limit = 50000
            plan_name = "Free"

        remaining_tokens = (
            None if token_limit is None
            else max(token_limit - used_tokens, 0)
        )

        return {
            "plan_name": plan_name,
            "token_limit": token_limit,
            "used_tokens": used_tokens,
            "remaining_tokens": remaining_tokens,
            "reset_after": "24h",
        }