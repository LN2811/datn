import uuid

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.models import Assignments, Criteria, Questions


class QuestionService:
    @staticmethod
    def _assignment_field():
        if hasattr(Questions, "assignment_id"):
            return getattr(Questions, "assignment_id")
        if hasattr(Questions, "assignments_id"):
            return getattr(Questions, "assignments_id")
        return None

    def get_questions(self, *, session: Session, assignment_id: uuid.UUID):
        assignment = session.get(Assignments, assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        assignment_field = self._assignment_field()
        if assignment_field is None:
            raise HTTPException(
                status_code=500,
                detail="Question model does not define assignment reference field",
            )

        statement = (
            select(Questions, Criteria)
            .join(Criteria, Questions.criteria_id == Criteria.id)
            .where(assignment_field == assignment_id)
            .order_by(Questions.created_at.desc())
        )

        results = session.exec(statement).all()
        return [
            {
                "id": str(question.id),
                "content": question.content,
                "assignment_id": str(assignment_id),
                "generated_by": question.generated_by,
                "created_at": question.created_at.isoformat(),
                "criteria": {
                    "id": str(criteria.id),
                    "name": criteria.name,
                    "description": criteria.description,
                },
            }
            for question, criteria in results
        ]

    def create_question(
        self,
        *,
        session: Session,
        assignment_id: uuid.UUID,
        criteria_id: uuid.UUID,
        content: str,
        generated_by: str = "ai",
    ):
        assignment = session.get(Assignments, assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        criteria = session.get(Criteria, criteria_id)
        if not criteria:
            raise HTTPException(status_code=404, detail="Criteria not found")

        question_data = {
            "project_id": assignment.project_id,
            "criteria_id": criteria_id,
            "content": content,
            "generated_by": generated_by,
        }

        if hasattr(Questions, "assignment_id"):
            question_data["assignment_id"] = assignment_id
        elif hasattr(Questions, "assignments_id"):
            question_data["assignments_id"] = assignment_id

        question = Questions(**question_data)
        session.add(question)
        session.commit()
        session.refresh(question)
        return question
