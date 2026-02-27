import uuid
from datetime import datetime
from typing import Optional

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

        track_ai_usage = generated_by == "ai"
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

        flow_lines: list[str] = []
        if flow_analysis:
            flow_lines.append(flow_analysis)
        if strengths:
            flow_lines.append(f"Strengths: {strengths}")
        if weaknesses:
            flow_lines.append(f"Weaknesses: {weaknesses}")
        if all(score is not None for score in [code_quality_score, logic_score, performance_score]):
            flow_lines.append(
                "Scores - code_quality: "
                f"{code_quality_score}, logic: {logic_score}, performance: {performance_score}"
            )

        feedback = AICodeFeedback(
            submission_id=submission_id,
            overview=overview,
            flow_analysis="\n".join(flow_lines) if flow_lines else None,
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

        session.add(feedback)

        if all([
            code_quality_score is not None,
            logic_score is not None,
            performance_score is not None
        ]):
            final_score = (
                code_quality_score +
                logic_score +
                performance_score
            ) / 3

            self._set_if_present(submission, "score", final_score)
            self._set_if_present(submission, "status", "graded")
            self._set_if_present(submission, "graded_at", datetime.utcnow())
            session.add(submission)

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

        if hasattr(feedback, "submission_id"):
            submission = session.get(CodeSubmissions, feedback.submission_id)
            if submission and all(
                score is not None for score in [code_quality_score, logic_score, performance_score]
            ):
                final_score = (code_quality_score + logic_score + performance_score) / 3
                self._set_if_present(submission, "score", final_score)
                self._set_if_present(submission, "status", "graded")
                self._set_if_present(submission, "graded_at", datetime.utcnow())
                session.add(submission)

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
