import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.Ai_code_feedback import AICodeFeedbackService

router = APIRouter()


class AICodeFeedbackCreateBody(BaseModel):
    submission_id: uuid.UUID
    overview: str
    flow_analysis: str | None = None
    improvement_suggestions: str | None = None
    generated_by: str = "ai"
    code_quality_score: float | None = None
    logic_score: float | None = None
    performance_score: float | None = None
    strengths: str | None = None
    weaknesses: str | None = None
    model_name: str = "gpt-4o"
    tokens_used: int | None = None


class AICodeFeedbackUpdateBody(BaseModel):
    overview: str | None = None
    flow_analysis: str | None = None
    code_quality_score: float | None = None
    logic_score: float | None = None
    performance_score: float | None = None
    strengths: str | None = None
    weaknesses: str | None = None
    improvement_suggestions: str | None = None


@router.post("")
def create_feedback(
    payload: AICodeFeedbackCreateBody,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return AICodeFeedbackService().create(
        session=session,
        submission_id=payload.submission_id,
        overview=payload.overview,
        flow_analysis=payload.flow_analysis,
        improvement_suggestions=payload.improvement_suggestions,
        generated_by=payload.generated_by,
        code_quality_score=payload.code_quality_score,
        logic_score=payload.logic_score,
        performance_score=payload.performance_score,
        strengths=payload.strengths,
        weaknesses=payload.weaknesses,
        model_name=payload.model_name,
        tokens_used=payload.tokens_used,
    )


@router.get("/submission/{submission_id}")
def get_feedback_by_submission(
    submission_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return AICodeFeedbackService().get_by_submission(
        session=session,
        submission_id=submission_id,
    )


@router.patch("/{feedback_id}")
def update_feedback(
    feedback_id: uuid.UUID,
    payload: AICodeFeedbackUpdateBody,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return AICodeFeedbackService().update(
        session=session,
        feedback_id=feedback_id,
        overview=payload.overview,
        flow_analysis=payload.flow_analysis,
        code_quality_score=payload.code_quality_score,
        logic_score=payload.logic_score,
        performance_score=payload.performance_score,
        strengths=payload.strengths,
        weaknesses=payload.weaknesses,
        improvement_suggestions=payload.improvement_suggestions,
    )


@router.delete("/{feedback_id}")
def delete_feedback(
    feedback_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
) -> dict:
    return AICodeFeedbackService().delete(
        session=session,
        feedback_id=feedback_id,
    )


@router.get("/admin/stats")
def admin_feedback_stats(
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return AICodeFeedbackService().admin_stats(session=session)
