import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.questions import QuestionService

router = APIRouter()


class QuestionCreateBody(BaseModel):
    criteria_id: uuid.UUID
    content: str
    generated_by: str = "ai"


@router.get("/assignment/{assignment_id}")
def get_questions(
    assignment_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
) -> list[dict]:
    return QuestionService().get_questions(
        session=session,
        assignment_id=assignment_id,
    )


@router.post("/assignment/{assignment_id}")
def create_question(
    assignment_id: uuid.UUID,
    question_in: QuestionCreateBody,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return QuestionService().create_question(
        session=session,
        assignment_id=assignment_id,
        criteria_id=question_in.criteria_id,
        content=question_in.content,
        generated_by=question_in.generated_by,
    )
