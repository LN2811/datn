import uuid
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.models import AIUsageLogs, PricingPlans, Projects, UserSubscriptions


class PricingPlanService:
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _is_subscription_active(subscription: UserSubscriptions) -> bool:
        if hasattr(subscription, "is_active") and getattr(subscription, "is_active") is False:
            return False
        if subscription.end_date and subscription.end_date < datetime.utcnow():
            return False
        return True

    def _get_active_subscription(self, *, user_id: uuid.UUID) -> Optional[UserSubscriptions]:
        subs = self.session.exec(
            select(UserSubscriptions).where(UserSubscriptions.user_id == user_id)
        ).all()
        subs = sorted(subs, key=lambda item: item.start_date, reverse=True)
        for subscription in subs:
            if self._is_subscription_active(subscription):
                return subscription
        return None

    def check_project_limit(self, *, user_id: uuid.UUID):
        subscription = self._get_active_subscription(user_id=user_id)
        if not subscription:
            raise HTTPException(status_code=403, detail="No active subscription found")

        plan = self.session.get(PricingPlans, subscription.plan_id)
        if not plan:
            raise HTTPException(status_code=403, detail="Subscription plan not found")

        max_projects = getattr(plan, "max_projects", None)
        if not max_projects:
            return

        owner_field = "owner_id" if hasattr(Projects, "owner_id") else "user_id"
        project_count = self.session.exec(
            select(func.count(Projects.id)).where(getattr(Projects, owner_field) == user_id)
        ).one()

        if project_count >= max_projects:
            raise HTTPException(
                status_code=403,
                detail=f"Project limit reached for {plan.name} plan",
            )

    def check_ai_limit(self, *, user_id: uuid.UUID):
        subscription = self._get_active_subscription(user_id=user_id)
        if not subscription:
            raise HTTPException(status_code=403, detail="No active subscription found")

        plan = self.session.get(PricingPlans, subscription.plan_id)
        if not plan:
            raise HTTPException(status_code=403, detail="Subscription plan not found")
        if not plan.ai_usage_limit:
            return

        now = datetime.utcnow()
        start_of_month = datetime(now.year, now.month, 1)
        used_tokens = self.session.exec(
            select(func.coalesce(func.sum(AIUsageLogs.tokens_used), 0)).where(
                AIUsageLogs.user_id == user_id,
                AIUsageLogs.created_at >= start_of_month,
            )
        ).one()

        if used_tokens >= plan.ai_usage_limit:
            raise HTTPException(status_code=403, detail="AI usage limit exceeded")
