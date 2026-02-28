import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.AssessmentAttempt import AssessmentAttemptService

router = APIRouter()


class StartAttemptBody(BaseModel):
    project_id: uuid.UUID
    assignment_id: uuid.UUID | None = None


class SaveAttemptBody(BaseModel):
    question_id: uuid.UUID
    score: int


@router.post("/start")
def start_attempt(
    attempt_in: StartAttemptBody,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
):
    return AssessmentAttemptService().start_attempt(
        session=session,
        project_id=attempt_in.project_id,
        user_id=current_user.id,
        assignment_id=attempt_in.assignment_id,
    )


@router.post("/{attempt_id}/save")
def save_attempt(
    attempt_id: uuid.UUID,
    answer_in: SaveAttemptBody,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
):
    return AssessmentAttemptService().save_attempt(
        session=session,
        attempt_id=attempt_id,
        question_id=answer_in.question_id,
        user_id=current_user.id,
        score=answer_in.score,
    )


@router.post("/{attempt_id}/submit")
def submit_attempt(
    attempt_id: uuid.UUID,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
):
    return AssessmentAttemptService().submit_attempt(
        session=session,
        attempt_id=attempt_id,
        user_id=current_user.id,
    )
