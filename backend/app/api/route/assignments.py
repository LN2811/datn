import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Assignments, CurriculumModules, Curriculums, Users
from app.services.assignment import AssignmentService

router = APIRouter()


class AssignmentCreateBody(BaseModel):
    title: str
    description: str | None = None
    curriculum_module_id: uuid.UUID | None = None
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
        curriculum_module_id=assignment_in.curriculum_module_id,
        difficulty_level=assignment_in.difficulty_level,
        assignment_type=assignment_in.assignment_type,
        generated_by=assignment_in.generated_by,
        max_score=assignment_in.max_score,
        is_active=assignment_in.is_active,
        due_date=assignment_in.due_date,
    )


@router.get("/modules/{module_id}/assignment")
def get_assignment_by_module(
    module_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    assignment = session.exec(
        select(Assignments).where(
            Assignments.curriculum_module_id == module_id
        )
    ).first()

    if not assignment:
        module = session.get(CurriculumModules, module_id)
        if module:
            curriculum = session.get(Curriculums, module.curriculum_id)
            if curriculum:
                assignment = session.exec(
                    select(Assignments).where(
                        Assignments.project_id == curriculum.project_id,
                        Assignments.title.endswith(f"({module.id.hex[:8]})"),
                    )
                ).first()
                if assignment and assignment.curriculum_module_id is None:
                    assignment.curriculum_module_id = module_id
                    session.add(assignment)
                    session.commit()
                    session.refresh(assignment)

    if not assignment:
        module = session.get(CurriculumModules, module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        curriculum = session.get(Curriculums, module.curriculum_id)
        if not curriculum:
            raise HTTPException(status_code=404, detail="Curriculum not found")
        assignment = Assignments(
            project_id=curriculum.project_id,
            curriculum_module_id=module_id,
            title=f"Nộp code GitHub - {module.title}",
            description=(
                "Nộp repository GitHub cho module này để AI đọc source code, "
                "chấm điểm và trả feedback."
            ),
        )
        if hasattr(assignment, "assignment_type"):
            assignment.assignment_type = "coding"
        if hasattr(assignment, "generated_by"):
            assignment.generated_by = "system"
        if hasattr(assignment, "max_score"):
            assignment.max_score = 10.0
        if hasattr(assignment, "is_active"):
            assignment.is_active = True
        session.add(assignment)
        session.commit()
        session.refresh(assignment)

    return assignment
