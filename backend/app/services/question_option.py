import uuid
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.models import Questions

try:
    from app.models.models import QuestionOptions  # type: ignore
except ImportError:  # pragma: no cover - compatibility when model is missing
    QuestionOptions = None  # type: ignore


class QuestionOptionService:
    @staticmethod
    def _ensure_model_available() -> None:
        if QuestionOptions is None:
            raise HTTPException(
                status_code=501,
                detail="QuestionOptions model is not configured in app.models.models",
            )

    @staticmethod
    def _dump_payload(schema_obj: Any) -> dict:
        if hasattr(schema_obj, "model_dump"):
            return schema_obj.model_dump(exclude_unset=True)
        if hasattr(schema_obj, "dict"):
            return schema_obj.dict(exclude_unset=True)
        return {}

    def create(
        self,
        *,
        session: Session,
        question_id: uuid.UUID,
        option_in: Any,
    ):
        self._ensure_model_available()
        payload = self._dump_payload(option_in)
        payload_question_id = payload.get("question_id", question_id)

        question = session.get(Questions, payload_question_id)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        if getattr(question, "question_type", None) == "single_choice" and payload.get("is_correct"):
            existing_correct_option = session.exec(
                select(QuestionOptions).where(
                    QuestionOptions.question_id == payload_question_id,
                    QuestionOptions.is_correct == True,
                )
            ).first()
            if existing_correct_option:
                raise HTTPException(
                    status_code=400,
                    detail="A correct option already exists for this question",
                )

        payload["question_id"] = payload_question_id
        new_option = QuestionOptions(**payload)
        session.add(new_option)
        session.commit()
        session.refresh(new_option)
        return new_option

    def update(
        self,
        *,
        session: Session,
        option_id: uuid.UUID,
        option_in: Any,
    ):
        self._ensure_model_available()
        option = session.get(QuestionOptions, option_id)
        if not option:
            raise HTTPException(status_code=404, detail="Option not found")

        update_data = self._dump_payload(option_in)
        if update_data.get("is_correct") is True:
            existing_correct_option = session.exec(
                select(QuestionOptions).where(
                    QuestionOptions.question_id == option.question_id,
                    QuestionOptions.is_correct == True,
                    QuestionOptions.id != option_id,
                )
            ).first()
            if existing_correct_option:
                raise HTTPException(
                    status_code=400,
                    detail="A correct option already exists for this question",
                )

        for key, value in update_data.items():
            if hasattr(option, key):
                setattr(option, key, value)

        session.add(option)
        session.commit()
        session.refresh(option)
        return option

    def delete(
        self,
        *,
        session: Session,
        option_id: uuid.UUID,
    ):
        self._ensure_model_available()
        option = session.get(QuestionOptions, option_id)
        if not option:
            raise HTTPException(status_code=404, detail="Option not found")
        session.delete(option)
        session.commit()

    def get_by_question(
        self,
        *,
        session: Session,
        question_id: uuid.UUID,
    ):
        self._ensure_model_available()
        return session.exec(
            select(QuestionOptions).where(QuestionOptions.question_id == question_id)
        ).all()
