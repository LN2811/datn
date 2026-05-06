import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.Pricing_plans import PricingPlanService

router = APIRouter()


def _target_user_id(
    current_user: Users,
    user_id: Optional[uuid.UUID],
) -> uuid.UUID:
    if user_id is None or user_id == current_user.id:
        return current_user.id

    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")

    return user_id


@router.get("/pricing-plans")
def get_pricing_plans(
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
) -> list[dict]:
    return PricingPlanService(session).get_pricing_plans()


@router.get("/subscriptions/me/current")
def get_my_current_subscription(
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
) -> Optional[dict]:
    return PricingPlanService(session).get_current_subscription(
        user_id=current_user.id,
    )


@router.post("/subscriptions/me/subscribe/{plan_id}")
def subscribe_my_plan(
    plan_id: uuid.UUID,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
) -> dict:
    return PricingPlanService(session).subscribe_plan(
        user_id=current_user.id,
        plan_id=plan_id,
    )


@router.get("/check-project-limit")
def check_project_limit(
    session: SessionDep,
    user_id: Optional[uuid.UUID] = None,
    current_user: Users = Depends(Authen.get_current_user),
) -> dict:
    target = _target_user_id(current_user, user_id)

    PricingPlanService(session).check_project_limit(user_id=target)

    return {
        "user_id": str(target),
        "project_limit_ok": True,
    }


@router.get("/check-ai-limit")
def check_ai_limit(
    session: SessionDep,
    user_id: Optional[uuid.UUID] = None,
    current_user: Users = Depends(Authen.get_current_user),
) -> dict:
    target = _target_user_id(current_user, user_id)

    PricingPlanService(session).check_ai_limit(user_id=target)

    return {
        "user_id": str(target),
        "ai_limit_ok": True,
    }