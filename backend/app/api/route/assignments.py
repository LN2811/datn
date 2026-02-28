import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.assignment import AssignmentService

router = APIRouter()


class AssignmentCreateBody(BaseModel):
    title: str
    description: str | None = None
    difficulty_level: str | None = None
    assignment_type: str | None = None
    generated_by: str | None = None
    max_score: float | None = None
    is_active: bool | None = None
    due_date: datetime | None = None


@router.get("/project/{project_id}")
def get_assignments(
    project_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
) -> list[dict]:
    return AssignmentService().get_assignments(
        project_id=project_id,
        session=session,
    )


@router.post("/project/{project_id}")
def create_assignment(
    project_id: uuid.UUID,
    assignment_in: AssignmentCreateBody,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
) -> dict:
    return AssignmentService().create_assignment(
        session=session,
        project_id=project_id,
        title=assignment_in.title,
        description=assignment_in.description,
        difficulty_level=assignment_in.difficulty_level,
        assignment_type=assignment_in.assignment_type,
        generated_by=assignment_in.generated_by,
        max_score=assignment_in.max_score,
        is_active=assignment_in.is_active,
        due_date=assignment_in.due_date,
    )
