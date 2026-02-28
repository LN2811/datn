import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.Pricing_plans import PricingPlanService

router = APIRouter()


def _target_user_id(current_user: Users, user_id: uuid.UUID | None) -> uuid.UUID:
    if user_id is None or user_id == current_user.id:
        return current_user.id
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    return user_id


@router.get("/check-project-limit")
def check_project_limit(
    session: SessionDep,
    user_id: uuid.UUID | None = None,
    current_user: Users = Depends(Authen.get_current_user),
) -> dict:
    target = _target_user_id(current_user, user_id)
    PricingPlanService(session).check_project_limit(user_id=target)
    return {"user_id": str(target), "project_limit_ok": True}


@router.get("/check-ai-limit")
def check_ai_limit(
    session: SessionDep,
    user_id: uuid.UUID | None = None,
    current_user: Users = Depends(Authen.get_current_user),
) -> dict:
    target = _target_user_id(current_user, user_id)
    PricingPlanService(session).check_ai_limit(user_id=target)
    return {"user_id": str(target), "ai_limit_ok": True}
