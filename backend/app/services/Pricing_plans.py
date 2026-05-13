import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.models import AIUsageLogs, PricingPlans, Projects, UserSubscriptions


class PricingPlanService:
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _dump_payload(schema_obj: Any) -> dict:
        if hasattr(schema_obj, "model_dump"):
            return schema_obj.model_dump(exclude_unset=True)
        if hasattr(schema_obj, "dict"):
            return schema_obj.dict(exclude_unset=True)
        return dict(schema_obj or {})

    @staticmethod
    def _normalize_payload(payload: dict) -> dict:
        payload = dict(payload)
        if "max_project" not in payload and "max_projects" in payload:
            payload["max_project"] = payload["max_projects"]
        if "bagde_text" not in payload and "badge_text" in payload:
            payload["bagde_text"] = payload["badge_text"]
        return payload

    @staticmethod
    def _serialize_plan(plan: PricingPlans) -> dict:
        max_project = getattr(plan, "max_project", None)
        badge_text = getattr(plan, "bagde_text", None)
        return {
            "id": str(plan.id),
            "name": plan.name,
            "description": plan.description,
            "price": plan.price,
            "ai_usage_limit": plan.ai_usage_limit,
            "billing_cycle": getattr(plan, "billing_cycle", "monthly"),
            "max_project": max_project,
            "max_projects": max_project,
            "is_active": getattr(plan, "is_active", True),
            "is_featured": getattr(plan, "is_featured", False),
            "display_order": getattr(plan, "display_order", 0),
            "bagde_text": badge_text,
            "badge_text": badge_text,
            "created_at": plan.created_at,
            "update_at": getattr(plan, "update_at", None),
        }

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

    def get_pricing_plans(self) -> list[dict]:
        plans = self.session.exec(
            select(PricingPlans).order_by(PricingPlans.display_order, PricingPlans.price, PricingPlans.name)
        ).all()
        return [self._serialize_plan(plan) for plan in plans]

    def get_current_subscription(self, *, user_id: uuid.UUID) -> Optional[dict]:
        subscription = self._get_active_subscription(user_id=user_id)
        if not subscription:
            return None

        plan = self.session.get(PricingPlans, subscription.plan_id)
        return {
            "id": str(subscription.id),
            "user_id": str(subscription.user_id),
            "plan_id": str(subscription.plan_id),
            "start_date": subscription.start_date,
            "end_date": subscription.end_date,
            "plan": self._serialize_plan(plan) if plan else None,
        }

    def create_pricing_plan(self, plan_in: Any) -> dict:
        payload = self._normalize_payload(self._dump_payload(plan_in))
        name = str(payload.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Plan name is required")

        existing_plan = self.session.exec(select(PricingPlans).where(PricingPlans.name == name)).first()
        if existing_plan:
            raise HTTPException(status_code=400, detail="Plan name already exists")

        price = float(payload.get("price") or 0)
        if price < 0:
            raise HTTPException(status_code=400, detail="Price must be greater than or equal to 0")

        new_plan = PricingPlans(
            name=name,
            description=payload.get("description"),
            price=price,
            ai_usage_limit=payload.get("ai_usage_limit"),
            billing_cycle=payload.get("billing_cycle") or "monthly",
            max_project=payload.get("max_project"),
            is_active=payload.get("is_active", True),
            is_featured=payload.get("is_featured", False),
            display_order=payload.get("display_order") or 0,
            bagde_text=payload.get("bagde_text"),
            created_at=datetime.utcnow(),
        )

        self.session.add(new_plan)
        self.session.commit()
        self.session.refresh(new_plan)
        return self._serialize_plan(new_plan)

    def update_pricing_plan(self, *, plan_id: uuid.UUID, plan_in: Any) -> dict:
        plan = self.session.get(PricingPlans, plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        payload = self._normalize_payload(self._dump_payload(plan_in))
        if "name" in payload:
            name = str(payload.get("name") or "").strip()
            if not name:
                raise HTTPException(status_code=400, detail="Plan name is required")
            existing_plan = self.session.exec(
                select(PricingPlans).where(PricingPlans.name == name, PricingPlans.id != plan_id)
            ).first()
            if existing_plan:
                raise HTTPException(status_code=400, detail="Plan name already exists")
            plan.name = name

        for field in (
            "description",
            "ai_usage_limit",
            "billing_cycle",
            "max_project",
            "is_active",
            "is_featured",
            "display_order",
            "bagde_text",
        ):
            if field in payload and hasattr(plan, field):
                setattr(plan, field, payload[field])

        if "price" in payload:
            price = float(payload.get("price") or 0)
            if price < 0:
                raise HTTPException(status_code=400, detail="Price must be greater than or equal to 0")
            plan.price = price

        plan.update_at = datetime.utcnow()
        self.session.add(plan)
        self.session.commit()
        self.session.refresh(plan)
        return self._serialize_plan(plan)

    def check_project_limit(self, *, user_id: uuid.UUID):
        subscription = self._get_active_subscription(user_id=user_id)
        if not subscription:
            raise HTTPException(status_code=403, detail="No active subscription found")

        plan = self.session.get(PricingPlans, subscription.plan_id)
        if not plan:
            raise HTTPException(status_code=403, detail="Subscription plan not found")

        max_projects = getattr(plan, "max_project", None)
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
