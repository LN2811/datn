import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.models import Answers, AssessmentAttempt
from app.services.assessment_Result import AssessmentResultService


class AssessmentAttemptService:
    @staticmethod
    def _is_attempt_time_up(attempt: AssessmentAttempt) -> bool:
        if not attempt.time_limit_minutes:
            return False
        expiry_time = attempt.started_at + timedelta(minutes=attempt.time_limit_minutes)
        return datetime.utcnow() > expiry_time

    def start_attempt(
        self,
        session: Session,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        assignment_id: uuid.UUID | None = None,
    ):
        statement = (
            select(AssessmentAttempt)
            .where(
                AssessmentAttempt.project_id == project_id,
                AssessmentAttempt.user_id == user_id,
                AssessmentAttempt.is_submitted == False,
            )
            .order_by(AssessmentAttempt.started_at.desc())
        )
        existing_attempt = session.exec(statement).first()
        if existing_attempt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An active attempt already exists for this user and project.",
            )

        new_attempt = AssessmentAttempt(
            project_id=project_id,
            assignment_id=assignment_id,
            user_id=user_id,
            started_at=datetime.utcnow(),
            is_submitted=False,
            is_time_up=False,
        )
        session.add(new_attempt)
        session.commit()
        session.refresh(new_attempt)

        return {
            "id": str(new_attempt.id),
            "project_id": str(new_attempt.project_id),
            "assignment_id": str(assignment_id) if assignment_id else None,
            "user_id": str(new_attempt.user_id),
            "started_at": new_attempt.started_at.isoformat(),
            "submitted_at": None,
            "is_submitted": new_attempt.is_submitted,
            "is_time_up": new_attempt.is_time_up,
        }

    def save_attempt(
        self,
        session: Session,
        attempt_id: uuid.UUID,
        question_id: uuid.UUID,
        user_id: uuid.UUID,
        score: int,
    ):
        attempt = session.get(AssessmentAttempt, attempt_id)
        if not attempt:
            raise HTTPException(status_code=404, detail="Attempt not found")
        if attempt.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        if attempt.is_submitted:
            raise HTTPException(
                status_code=400,
                detail="Cannot save answers for a submitted attempt",
            )
        if self._is_attempt_time_up(attempt):
            attempt.is_time_up = True
            attempt.is_submitted = True
            attempt.submitted_at = datetime.utcnow()
            session.add(attempt)
            session.commit()
            raise HTTPException(status_code=400, detail="Time is up for this attempt")

        existing = session.exec(
            select(Answers).where(
                Answers.attempt_id == attempt_id,
                Answers.question_id == question_id,
            )
        ).first()
        if existing:
            existing.score = score
            existing.answered_at = datetime.utcnow()
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing

        answer = Answers(
            attempt_id=attempt_id,
            question_id=question_id,
            user_id=user_id,
            score=score,
            answered_at=datetime.utcnow(),
        )
        session.add(answer)
        session.commit()
        session.refresh(answer)
        return answer

    def submit_attempt(
        self,
        session: Session,
        attempt_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        attempt = session.get(AssessmentAttempt, attempt_id)
        if not attempt:
            raise HTTPException(status_code=404, detail="Attempt not found")
        if attempt.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        if attempt.is_submitted:
            raise HTTPException(status_code=400, detail="Already submitted")

        if self._is_attempt_time_up(attempt):
            attempt.is_time_up = True
        attempt.is_submitted = True
        attempt.submitted_at = datetime.utcnow()
        session.add(attempt)
        session.commit()

        result_service = AssessmentResultService(session)
        return result_service.create_from_attempt(attempt_id)
