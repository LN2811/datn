import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.ai_service import ai_usage_tracking_context
from app.services.questions import QuestionService

router = APIRouter()


class QuestionCreateBody(BaseModel):
    criteria_id: uuid.UUID
    content: str
    generated_by: str = "ai"


class QuizAnswerBody(BaseModel):
    question_id: uuid.UUID
    selected_option_id: uuid.UUID


class QuizSubmitBody(BaseModel):
    answers: list[QuizAnswerBody]


@router.get("/assignment/{assignment_id}")
def get_questions(
    assignment_id: uuid.UUID,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
) -> list[dict]:
    with ai_usage_tracking_context(
        session=session,
        user_id=current_user.id,
        action_type="generate_questions",
    ):
        return QuestionService().get_questions(
            session=session,
            assignment_id=assignment_id,
        )


@router.get("/assignment/{assignment_id}/quiz")
def get_assignment_quiz(
    assignment_id: uuid.UUID,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
) -> dict:
    with ai_usage_tracking_context(
        session=session,
        user_id=current_user.id,
        action_type="generate_questions",
    ):
        return QuestionService().get_assignment_quiz(
            session=session,
            assignment_id=assignment_id,
            user_id=current_user.id,
        )


@router.post("/assignment/{assignment_id}/quiz/submit")
def submit_assignment_quiz(
    assignment_id: uuid.UUID,
    quiz_in: QuizSubmitBody,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
) -> dict:
    answers = [
        answer.model_dump() if hasattr(answer, "model_dump") else answer.dict()
        for answer in quiz_in.answers
    ]
    return QuestionService().submit_assignment_quiz(
        session=session,
        assignment_id=assignment_id,
        user_id=current_user.id,
        answers=answers,
    )


@router.get("/modules/{module_id}/quiz")
def get_module_quiz(
    module_id: uuid.UUID,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
) -> dict:
    with ai_usage_tracking_context(
        session=session,
        user_id=current_user.id,
        action_type="generate_questions",
    ):
        return QuestionService().get_module_quiz(
            session=session,
            module_id=module_id,
            user_id=current_user.id,
        )


@router.post("/modules/{module_id}/quiz/submit")
def submit_module_quiz(
    module_id: uuid.UUID,
    quiz_in: QuizSubmitBody,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
) -> dict:
    answers = [
        answer.model_dump() if hasattr(answer, "model_dump") else answer.dict()
        for answer in quiz_in.answers
    ]
    with ai_usage_tracking_context(
        session=session,
        user_id=current_user.id,
        action_type="generate_questions",
    ):
        return QuestionService().submit_module_quiz(
            session=session,
            module_id=module_id,
            user_id=current_user.id,
            answers=answers,
        )


@router.post("/assignment/{assignment_id}")
def create_question(
    assignment_id: uuid.UUID,
    question_in: QuestionCreateBody,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
):
    with ai_usage_tracking_context(
        session=session,
        user_id=current_user.id,
        action_type="generate_questions",
    ):
        return QuestionService().create_question(
            session=session,
            assignment_id=assignment_id,
            criteria_id=question_in.criteria_id,
            content=question_in.content,
            generated_by=question_in.generated_by,
            user_id=current_user.id,
        )
