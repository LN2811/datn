import uuid
from datetime import datetime, timedelta
from typing import Any, List, Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.models import Answers, AssessmentAttempt, Questions

try:
    from app.models.models import QuestionOptions  # type: ignore
except ImportError:  # pragma: no cover - compatibility when model is missing
    QuestionOptions = None  # type: ignore


class AnswerService:
    @staticmethod
    def _dump_payload(schema_obj: Any) -> dict:
        if hasattr(schema_obj, "model_dump"):
            return schema_obj.model_dump(exclude_unset=True)
        if hasattr(schema_obj, "dict"):
            return schema_obj.dict(exclude_unset=True)
        return {}

    @staticmethod
    def _set_if_present(model_obj, field_name: str, value) -> None:
        if value is not None and hasattr(model_obj, field_name):
            setattr(model_obj, field_name, value)

    @staticmethod
    def _resolve_auto_score(
        *,
        session: Session,
        question_id: uuid.UUID,
        selected_option_id: Optional[uuid.UUID],
        score: Optional[int],
        is_correct: Optional[bool],
    ) -> tuple[int, Optional[bool]]:
        resolved_score = score if score is not None else 1
        resolved_is_correct = is_correct

        if selected_option_id and QuestionOptions is not None:
            option = session.get(QuestionOptions, selected_option_id)
            if not option or option.question_id != question_id:
                raise HTTPException(
                    status_code=400,
                    detail="Selected option does not belong to the question",
                )

            resolved_is_correct = bool(getattr(option, "is_correct", False))
            if score is None:
                resolved_score = 5 if resolved_is_correct else 1

        return resolved_score, resolved_is_correct

    def create(
        self,
        *,
        session: Session,
        answer_in: Any,
    ) -> Answers:
        payload = self._dump_payload(answer_in)
        attempt_id = payload.get("attempt_id")
        question_id = payload.get("question_id")
        user_id = payload.get("user_id")
        score = payload.get("score")

        if not attempt_id or not question_id or not user_id:
            raise HTTPException(
                status_code=400,
                detail="attempt_id, question_id and user_id are required",
            )

        attempt = session.get(AssessmentAttempt, attempt_id)
        if not attempt:
            raise HTTPException(status_code=404, detail="Assessment attempt not found")
        if attempt.is_submitted:
            raise HTTPException(
                status_code=400,
                detail="Cannot submit answer for a submitted attempt",
            )
        if attempt.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        if attempt.time_limit_minutes:
            expiry_time = attempt.started_at + timedelta(minutes=attempt.time_limit_minutes)
            if datetime.utcnow() > expiry_time:
                attempt.is_time_up = True
                attempt.is_submitted = True
                attempt.submitted_at = datetime.utcnow()
                session.add(attempt)
                session.commit()
                raise HTTPException(status_code=400, detail="Time is up for this attempt")

        existing_answer = session.exec(
            select(Answers).where(
                Answers.attempt_id == attempt_id,
                Answers.question_id == question_id,
            )
        ).first()
        if existing_answer:
            raise HTTPException(
                status_code=400,
                detail="Answer already exists for this question in the attempt",
            )

        question = session.get(Questions, question_id)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        selected_option_id = payload.get("selected_option_id")
        resolved_score, resolved_is_correct = self._resolve_auto_score(
            session=session,
            question_id=question_id,
            selected_option_id=selected_option_id,
            score=score,
            is_correct=payload.get("is_correct"),
        )

        db_answer = Answers(
            question_id=question_id,
            user_id=user_id,
            attempt_id=attempt_id,
            score=resolved_score,
            answered_at=datetime.utcnow(),
        )

        # Keep compatibility with richer schemas in another branch.
        self._set_if_present(db_answer, "selected_option_id", selected_option_id)
        self._set_if_present(db_answer, "is_correct", resolved_is_correct)
        self._set_if_present(db_answer, "text_answer", payload.get("text_answer"))

        session.add(db_answer)
        session.commit()
        session.refresh(db_answer)
        return db_answer

    def get_by_attempt_id(
        self,
        *,
        session: Session,
        attempt_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> List[Answers]:
        attempt = session.get(AssessmentAttempt, attempt_id)
        if not attempt:
            raise HTTPException(status_code=404, detail="Assessment attempt not found")
        if user_id is not None and attempt.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        answers = session.exec(
            select(Answers)
            .join(Questions)
            .where(Answers.attempt_id == attempt_id)
            .order_by(Questions.created_at)
        ).all()
        return answers

    def update(
        self,
        *,
        session: Session,
        answer_id: uuid.UUID,
        answer_in: Any,
    ) -> Answers:
        db_answer = session.get(Answers, answer_id)
        if not db_answer:
            raise HTTPException(status_code=404, detail="Answer not found")

        attempt = session.get(AssessmentAttempt, db_answer.attempt_id)
        if not attempt:
            raise HTTPException(status_code=404, detail="Assessment attempt not found")
        if attempt.is_submitted:
            raise HTTPException(
                status_code=400,
                detail="Cannot update answer for a submitted attempt",
            )

        update_data = self._dump_payload(answer_in)
        if "selected_option_id" in update_data:
            fallback_score = (
                update_data["score"]
                if "score" in update_data
                else getattr(db_answer, "score", None)
            )
            resolved_score, resolved_is_correct = self._resolve_auto_score(
                session=session,
                question_id=db_answer.question_id,
                selected_option_id=update_data.get("selected_option_id"),
                score=fallback_score,
                is_correct=update_data.get(
                    "is_correct",
                    getattr(db_answer, "is_correct", None),
                ),
            )
            update_data["score"] = resolved_score
            update_data["is_correct"] = resolved_is_correct

        for key, value in update_data.items():
            if key in {"updated_at", "attempt_id", "question_id", "user_id"}:
                continue
            if hasattr(db_answer, key):
                setattr(db_answer, key, value)

        db_answer.answered_at = datetime.utcnow()
        session.add(db_answer)
        session.commit()
        session.refresh(db_answer)
        return db_answer
