import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.ai_Usage_Log import AIUsageService

router = APIRouter()


class AIUsageCreateBody(BaseModel):
    user_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    action_type: str
    model_name: str | None = None
    tokens_used: int


@router.post("")
def log_usage(
    payload: AIUsageCreateBody,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
):
    target_user_id = payload.user_id or current_user.id
    if target_user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")

    return AIUsageService().log_usage(
        session=session,
        user_id=target_user_id,
        project_id=payload.project_id,
        action_type=payload.action_type,
        model_name=payload.model_name,
        tokens_used=payload.tokens_used,
    )


@router.get("/monthly")
def get_monthly_usage(
    session: SessionDep,
    user_id: uuid.UUID | None = None,
    current_user: Users = Depends(Authen.get_current_user),
) -> dict:
    target_user_id = user_id or current_user.id
    if target_user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    return {
        "user_id": str(target_user_id),
        "monthly_tokens": AIUsageService().get_monthly_usage(
            session=session,
            user_id=target_user_id,
        ),
    }


@router.get("/admin/stats")
def admin_dashboard_stats(
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return AIUsageService().admin_dashboard_stats(session=session)
