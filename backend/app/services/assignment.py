import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.models import Assignments, Projects


class AssignmentService:
    @staticmethod
    def _set_if_present(model_obj, field_name: str, value) -> None:
        if value is not None and hasattr(model_obj, field_name):
            setattr(model_obj, field_name, value)

    def get_assigment(
        self,
        project_id: uuid.UUID,
        session: Session,
    ):
        return self.get_assignments(project_id=project_id, session=session)

    def get_assignments(
        self,
        *,
        project_id: uuid.UUID,
        session: Session,
    ):
        project = session.get(Projects, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        statement = (
            select(Assignments)
            .where(Assignments.project_id == project_id)
            .order_by(Assignments.created_at.desc())
        )
        results = session.exec(statement).all()

        return [
            {
                "id": str(assignment.id),
                "title": assignment.title,
                "description": assignment.description,
                "created_at": assignment.created_at.isoformat(),
            }
            for assignment in results
        ]

    def create_assignment(
        self,
        session: Session,
        project_id: uuid.UUID,
        title: str,
        description: str | None = None,
        *,
        difficulty_level: str | None = None,
        assignment_type: str | None = None,
        generated_by: str | None = None,
        max_score: float | None = None,
        is_active: bool | None = None,
        due_date: datetime | None = None,
    ):
        project = session.get(Projects, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        assignment = Assignments(
            project_id=project_id,
            title=title,
            description=description,
            created_at=datetime.utcnow(),
        )

        # Compatibility with richer schema variants.
        self._set_if_present(assignment, "difficulty_level", difficulty_level or "medium")
        self._set_if_present(assignment, "assignment_type", assignment_type or "coding")
        self._set_if_present(assignment, "generated_by", generated_by or "manual")
        self._set_if_present(assignment, "max_score", max_score if max_score is not None else 10.0)
        self._set_if_present(assignment, "is_active", is_active if is_active is not None else True)
        self._set_if_present(assignment, "due_date", due_date)

        session.add(assignment)
        session.commit()
        session.refresh(assignment)

        return {
            "id": str(assignment.id),
            "title": assignment.title,
            "description": assignment.description,
            "difficulty_level": getattr(assignment, "difficulty_level", None),
            "assignment_type": getattr(assignment, "assignment_type", None),
            "generated_by": getattr(assignment, "generated_by", None),
            "max_score": getattr(assignment, "max_score", None),
            "is_active": getattr(assignment, "is_active", None),
            "created_at": assignment.created_at.isoformat(),
        }
