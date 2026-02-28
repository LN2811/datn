import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.answers import AnswerService

router = APIRouter()


class AnswerCreateBody(BaseModel):
    attempt_id: uuid.UUID
    question_id: uuid.UUID
    score: int | None = None
    selected_option_id: uuid.UUID | None = None
    text_answer: str | None = None
    is_correct: bool | None = None


class AnswerUpdateBody(BaseModel):
    score: int | None = None
    selected_option_id: uuid.UUID | None = None
    text_answer: str | None = None
    is_correct: bool | None = None


@router.post("")
def create_answer(
    answer_in: AnswerCreateBody,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
):
    payload = answer_in.model_dump()
    payload["user_id"] = current_user.id
    return AnswerService().create(
        session=session,
        answer_in=payload,
    )


@router.get("/attempt/{attempt_id}")
def get_answers_by_attempt(
    attempt_id: uuid.UUID,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
):
    return AnswerService().get_by_attempt_id(
        session=session,
        attempt_id=attempt_id,
        user_id=current_user.id,
    )


@router.patch("/{answer_id}")
def update_answer(
    answer_id: uuid.UUID,
    answer_in: AnswerUpdateBody,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return AnswerService().update(
        session=session,
        answer_id=answer_id,
        answer_in=answer_in,
    )
