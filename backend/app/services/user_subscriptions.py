import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select, func

from app.models.models import AIUsageLogs, PricingPlans, UserSubscriptions


class UserSubscriptionService:
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _is_active(subscription: UserSubscriptions) -> bool:
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
        for sub in subs:
            if self._is_active(sub):
                return sub
        return None

    def subscribe(
        self,
        *,
        user_id: uuid.UUID,
        plan_id: uuid.UUID,
        duration_days: int = 30,
    ):
        plan = self.session.get(PricingPlans, plan_id)
        if not plan:
            raise HTTPException(status_code=400, detail="Invalid plan")
        if hasattr(plan, "is_active") and plan.is_active is False:
            raise HTTPException(status_code=400, detail="Invalid plan")

        old_subs = self.session.exec(
            select(UserSubscriptions).where(UserSubscriptions.user_id == user_id)
        ).all()
        now = datetime.utcnow()
        for sub in old_subs:
            if hasattr(sub, "is_active"):
                sub.is_active = False
            if not sub.end_date or sub.end_date > now:
                sub.end_date = now
            self.session.add(sub)

        new_subscription = UserSubscriptions(
            user_id=user_id,
            plan_id=plan_id,
            start_date=now,
            end_date=now + timedelta(days=duration_days),
        )
        if hasattr(new_subscription, "is_active"):
            new_subscription.is_active = True

        self.session.add(new_subscription)
        self.session.commit()
        self.session.refresh(new_subscription)
        return new_subscription

    def check_subscription(self, *, user_id: uuid.UUID):
        subscription = self._get_active_subscription(user_id=user_id)
        if not subscription:
            raise HTTPException(status_code=403, detail="No active subscription")

        if subscription.end_date and subscription.end_date < datetime.utcnow():
            if hasattr(subscription, "is_active"):
                subscription.is_active = False
                self.session.add(subscription)
                self.session.commit()
            raise HTTPException(status_code=403, detail="Subscription expired")

        plan = self.session.get(PricingPlans, subscription.plan_id)
        if not plan:
            raise HTTPException(status_code=403, detail="Invalid pricing plan")
        if hasattr(plan, "is_active") and plan.is_active is False:
            raise HTTPException(status_code=403, detail="Invalid pricing plan")

        now = datetime.utcnow()
        month_start = datetime(now.year, now.month, 1)
        total_tokens = self.session.exec(
            select(func.coalesce(func.sum(AIUsageLogs.tokens_used), 0)).where(
                AIUsageLogs.user_id == user_id,
                AIUsageLogs.created_at >= month_start,
            )
        ).one()

        remaining_tokens = None
        if plan.ai_usage_limit:
            if total_tokens >= plan.ai_usage_limit:
                raise HTTPException(status_code=403, detail="AI usage limit exceeded")
            remaining_tokens = plan.ai_usage_limit - total_tokens

        return {
            "subscription": subscription,
            "plan": plan,
            "tokens_used": total_tokens,
            "remaining_tokens": remaining_tokens,
        }

    def cancel_subscription(self, *, user_id: uuid.UUID):
        subscription = self._get_active_subscription(user_id=user_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="No active subscription")

        if hasattr(subscription, "is_active"):
            subscription.is_active = False
        subscription.end_date = datetime.utcnow()
        self.session.add(subscription)
        self.session.commit()
        return {"message": "Subscription cancelled"}

    def get_current_plan(self, *, user_id: uuid.UUID):
        data = self.check_subscription(user_id=user_id)
        return {
            "plan_name": data["plan"].name,
            "ai_limit": data["plan"].ai_usage_limit,
            "tokens_used": data["tokens_used"],
            "remaining_tokens": data["remaining_tokens"],
            "expires_at": data["subscription"].end_date,
        }
