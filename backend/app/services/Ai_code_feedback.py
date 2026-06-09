import json
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException
from sqlmodel import Session, select, func

from app.models.models import (
    AICodeFeedback,
    Assignments,
    CodeSubmissions,
)
from app.services.ai_Usage_Log import AIUsageService


class AICodeFeedbackService:

    def __init__(self):
        self.usage_service = AIUsageService()

    @staticmethod
    def _set_if_present(model_obj, field_name: str, value) -> None:
        if value is not None and hasattr(model_obj, field_name):
            setattr(model_obj, field_name, value)

    @staticmethod
    def _estimate_tokens(*parts: Optional[str]) -> int:
        total_chars = sum(len(part) for part in parts if part)
        return max(80, total_chars // 4)

    @staticmethod
    def _extract_json_object(value: Optional[str]) -> dict[str, Any] | None:
        if not value:
            return None

        cleaned = value.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end <= start:
            return None

        try:
            payload = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _to_float_or_none(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            score = float(value)
        except (TypeError, ValueError):
            return None
        return max(0.0, min(10.0, score))

    @staticmethod
    def _to_string_or_none(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, list):
            return "\n".join(str(item) for item in value if item is not None).strip() or None
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False)
        return str(value).strip() or None

    @staticmethod
    def _average_available_scores(*scores: Optional[float]) -> Optional[float]:
        available_scores = [score for score in scores if score is not None]
        if not available_scores:
            return None
        return sum(available_scores) / len(available_scores)

    @classmethod
    def _mark_submission_graded(
        cls,
        *,
        session: Session,
        submission: CodeSubmissions,
        code_quality_score: Optional[float],
        logic_score: Optional[float],
        performance_score: Optional[float],
    ) -> Optional[float]:
        final_score = cls._average_available_scores(
            code_quality_score,
            logic_score,
            performance_score,
        )
        if final_score is None:
            return None

        cls._set_if_present(submission, "score", final_score)
        cls._set_if_present(submission, "status", "graded")
        cls._set_if_present(submission, "graded_at", datetime.utcnow())
        session.add(submission)
        return final_score

    @classmethod
    def normalize_feedback_record(cls, feedback: AICodeFeedback) -> bool:
        payload = cls._extract_json_object(feedback.overview)
        if not payload:
            return False

        changed = False
        text_fields = [
            "overview",
            "flow_analysis",
            "strengths",
            "weaknesses",
            "improvement_suggestions",
        ]
        score_fields = [
            "code_quality_score",
            "logic_score",
            "performance_score",
        ]

        for field_name in text_fields:
            value = cls._to_string_or_none(payload.get(field_name))
            if value is not None and getattr(feedback, field_name, None) != value:
                setattr(feedback, field_name, value)
                changed = True

        overall_score = cls._to_float_or_none(payload.get("overall_score"))
        for field_name in score_fields:
            value = cls._to_float_or_none(payload.get(field_name))
            if value is None:
                value = overall_score
            if value is not None and getattr(feedback, field_name, None) != value:
                setattr(feedback, field_name, value)
                changed = True

        return changed

    @staticmethod
    def _resolve_project_id(
        *,
        session: Session,
        submission: CodeSubmissions,
    ) -> Optional[uuid.UUID]:
        assignment = session.get(Assignments, submission.assignment_id)
        if not assignment:
            return None
        return assignment.project_id

    def create(
        self,
        *,
        session: Session,
        submission_id: uuid.UUID,
        overview: str,
        flow_analysis: Optional[str] = None,
        improvement_suggestions: Optional[str] = None,
        generated_by: str = "ai",
        code_quality_score: Optional[float] = None,
        logic_score: Optional[float] = None,
        performance_score: Optional[float] = None,
        strengths: Optional[str] = None,
        weaknesses: Optional[str] = None,
        model_name: str = "gpt-4o",
        tokens_used: Optional[int] = None,
        track_usage: Optional[bool] = None,
    ) -> AICodeFeedback:

        submission = session.get(CodeSubmissions, submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        existing = session.exec(
            select(AICodeFeedback).where(
                AICodeFeedback.submission_id == submission_id
            )
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="Feedback already exists")

        track_ai_usage = generated_by == "ai" if track_usage is None else track_usage
        project_id = self._resolve_project_id(session=session, submission=submission)
        estimated_tokens = tokens_used or self._estimate_tokens(
            overview,
            flow_analysis,
            strengths,
            weaknesses,
            improvement_suggestions,
        )
        if track_ai_usage:
            self.usage_service.check_quota(
                session=session,
                user_id=submission.user_id,
                tokens_required=estimated_tokens,
            )
            self.usage_service.check_rate_limit(
                session=session,
                user_id=submission.user_id,
                action_type="generate_feedback",
            )

        feedback = AICodeFeedback(
            submission_id=submission_id,
            overview=overview,
            flow_analysis=flow_analysis,
            improvement_suggestions=improvement_suggestions,
            created_at=datetime.utcnow()
        )

        # Keep compatibility if the model has extra columns in another branch/migration.
        self._set_if_present(feedback, "generated_by", generated_by)
        self._set_if_present(feedback, "code_quality_score", code_quality_score)
        self._set_if_present(feedback, "logic_score", logic_score)
        self._set_if_present(feedback, "performance_score", performance_score)
        self._set_if_present(feedback, "strengths", strengths)
        self._set_if_present(feedback, "weaknesses", weaknesses)
        self.normalize_feedback_record(feedback)

        session.add(feedback)

        self._mark_submission_graded(
            session=session,
            submission=submission,
            code_quality_score=getattr(feedback, "code_quality_score", None),
            logic_score=getattr(feedback, "logic_score", None),
            performance_score=getattr(feedback, "performance_score", None),
        )

        session.commit()
        session.refresh(feedback)

        if track_ai_usage:
            self.usage_service.log_usage(
                session=session,
                user_id=submission.user_id,
                project_id=project_id,
                action_type="generate_feedback",
                model_name=model_name,
                tokens_used=estimated_tokens,
            )

        return feedback

    def get_by_submission(
        self,
        *,
        session: Session,
        submission_id: uuid.UUID
    ) -> AICodeFeedback:

        feedback = session.exec(
            select(AICodeFeedback).where(
                AICodeFeedback.submission_id == submission_id
            )
        ).first()

        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")

        return feedback

    def update(
        self,
        *,
        session: Session,
        feedback_id: uuid.UUID,
        overview: Optional[str] = None,
        flow_analysis: Optional[str] = None,
        code_quality_score: Optional[float] = None,
        logic_score: Optional[float] = None,
        performance_score: Optional[float] = None,
        strengths: Optional[str] = None,
        weaknesses: Optional[str] = None,
        improvement_suggestions: Optional[str] = None
    ) -> AICodeFeedback:

        feedback = session.get(AICodeFeedback, feedback_id)
        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")

        if overview is not None:
            feedback.overview = overview
        if flow_analysis is not None:
            feedback.flow_analysis = flow_analysis
        if improvement_suggestions is not None:
            feedback.improvement_suggestions = improvement_suggestions

        self._set_if_present(feedback, "code_quality_score", code_quality_score)
        self._set_if_present(feedback, "logic_score", logic_score)
        self._set_if_present(feedback, "performance_score", performance_score)
        self._set_if_present(feedback, "strengths", strengths)
        self._set_if_present(feedback, "weaknesses", weaknesses)
        self.normalize_feedback_record(feedback)

        if hasattr(feedback, "submission_id"):
            submission = session.get(CodeSubmissions, feedback.submission_id)
            if submission:
                self._mark_submission_graded(
                    session=session,
                    submission=submission,
                    code_quality_score=getattr(feedback, "code_quality_score", None),
                    logic_score=getattr(feedback, "logic_score", None),
                    performance_score=getattr(feedback, "performance_score", None),
                )

        session.add(feedback)
        session.commit()
        session.refresh(feedback)

        return feedback

    def delete(
        self,
        *,
        session: Session,
        feedback_id: uuid.UUID
    ):

        feedback = session.get(AICodeFeedback, feedback_id)
        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")

        session.delete(feedback)
        session.commit()

        return {"message": "Feedback deleted"}

    def admin_stats(
        self,
        *,
        session: Session
    ):
        total_feedbacks = session.exec(
            select(func.count(AICodeFeedback.id))
        ).one()

        avg_quality = None
        avg_logic = None
        avg_performance = None

        if hasattr(AICodeFeedback, "code_quality_score"):
            avg_quality = session.exec(
                select(func.avg(getattr(AICodeFeedback, "code_quality_score")))
            ).one()
        if hasattr(AICodeFeedback, "logic_score"):
            avg_logic = session.exec(
                select(func.avg(getattr(AICodeFeedback, "logic_score")))
            ).one()
        if hasattr(AICodeFeedback, "performance_score"):
            avg_performance = session.exec(
                select(func.avg(getattr(AICodeFeedback, "performance_score")))
            ).one()

        return {
            "total_feedbacks": total_feedbacks or 0,
            "avg_quality": avg_quality or 0,
            "avg_logic": avg_logic or 0,
            "avg_performance": avg_performance or 0
        }
