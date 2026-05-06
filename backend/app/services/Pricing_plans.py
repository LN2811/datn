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

    def subscribe_plan(
            self,
            *,
            user_id: uuid.UUID,
            plan_id: uuid.UUID,
    )-> dict:
        plan = self.session.get(PricingPlans, plan_id)

        if not plan:
            raise HTTPException(status_code = 404, detail = "Plan not found")

        if hasattr(plan, "is_active") and getattr(plan, "is_active") is False:
            raise HTTPException(status_code = 400, detail= "Plan is not active")

        current_subscription = self._get_active_subscription(user_id= user_id)
        if current_subscription and current_subscription.plan_id == plan_id:
            return{
                "id": str(current_subscription.id),
                "user_id": str(current_subscription.user_id),
                "plan_id": str(current_subscription.plan_id),
                "plan_name": plan.name,
                "is_active": True,
                "message": "You are already subscribed to this plan",
            }
        if current_subscription:
            current_subscription.end_date = datetime.utcnow()
            if hasattr(current_subscription, "is_active"):
                setattr(current_subscription, "is_active", False)

            self.session.add(current_subscription)

        new_subscription = UserSubscriptions(
            user_id= user_id,
            plan_id=plan_id,
            start_date= datetime.utcnow(),
            end_date= None,
        )
        if hasattr(new_subscription, "is_active"):
            setattr(new_subscription, "is_active", True)

        self.session.add(new_subscription)
        self.session.commit()
        self.session.refresh(new_subscription)
        return{
            "id": str(new_subscription.id),
            "user_id": str(new_subscription.user_id),
            "plan_id": str(new_subscription.plan_id),
            "plan_name": plan.name,
            "is_active": True,
            "message": "Subscribed successfully",
        }
