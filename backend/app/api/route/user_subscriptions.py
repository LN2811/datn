import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.user_subscriptions import UserSubscriptionService

router = APIRouter()


class SubscribeBody(BaseModel):
    plan_id: uuid.UUID
    duration_days: int = 30
    user_id: uuid.UUID | None = None


def _target_user_id(current_user: Users, user_id: uuid.UUID | None) -> uuid.UUID:
    if user_id is None or user_id == current_user.id:
        return current_user.id
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    return user_id


@router.post("/subscribe")
def subscribe(
    payload: SubscribeBody,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
):
    target = _target_user_id(current_user, payload.user_id)
    return UserSubscriptionService(session).subscribe(
        user_id=target,
        plan_id=payload.plan_id,
        duration_days=payload.duration_days,
    )


@router.get("/check")
def check_subscription(
    session: SessionDep,
    user_id: uuid.UUID | None = None,
    current_user: Users = Depends(Authen.get_current_user),
):
    target = _target_user_id(current_user, user_id)
    return UserSubscriptionService(session).check_subscription(user_id=target)


@router.post("/cancel")
def cancel_subscription(
    session: SessionDep,
    user_id: uuid.UUID | None = None,
    current_user: Users = Depends(Authen.get_current_user),
) -> dict:
    target = _target_user_id(current_user, user_id)
    return UserSubscriptionService(session).cancel_subscription(user_id=target)


@router.get("/current-plan")
def get_current_plan(
    session: SessionDep,
    user_id: uuid.UUID | None = None,
    current_user: Users = Depends(Authen.get_current_user),
):
    target = _target_user_id(current_user, user_id)
    return UserSubscriptionService(session).get_current_plan(user_id=target)
