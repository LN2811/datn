import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.question_option import QuestionOptionService

router = APIRouter()


class QuestionOptionCreateBody(BaseModel):
    content: str
    is_correct: bool = False
    order_index: int | None = None


class QuestionOptionUpdateBody(BaseModel):
    content: str | None = None
    is_correct: bool | None = None
    order_index: int | None = None


@router.get("/questions/{question_id}")
def get_options_by_question(
    question_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return QuestionOptionService().get_by_question(
        session=session,
        question_id=question_id,
    )


@router.post("/questions/{question_id}")
def create_option(
    question_id: uuid.UUID,
    option_in: QuestionOptionCreateBody,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return QuestionOptionService().create(
        session=session,
        question_id=question_id,
        option_in=option_in,
    )


@router.patch("/{option_id}")
def update_option(
    option_id: uuid.UUID,
    option_in: QuestionOptionUpdateBody,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return QuestionOptionService().update(
        session=session,
        option_id=option_id,
        option_in=option_in,
    )


@router.delete("/{option_id}")
def delete_option(
    option_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
) -> dict:
    QuestionOptionService().delete(
        session=session,
        option_id=option_id,
    )
    return {"id": str(option_id), "message": "Option deleted"}
