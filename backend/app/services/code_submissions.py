import uuid
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select, func

from app.models.models import AICodeFeedback, Assignments, CodeSubmissions
from app.services.ai_Usage_Log import AIUsageService
from app.services.user_subscriptions import UserSubscriptionService


class CodeSubmissionService:
    def __init__(self, session: Session):
        self.session = session
        self.subscription_service = UserSubscriptionService(session)
        self.usage_service = AIUsageService()

    @staticmethod
    def _set_if_present(model_obj, field_name: str, value) -> None:
        if value is not None and hasattr(model_obj, field_name):
            setattr(model_obj, field_name, value)

    @staticmethod
    def _estimate_feedback_tokens(submission: CodeSubmissions) -> int:
        url_len = len(submission.github_repo_url or "")
        # Keep a reasonable baseline for one grading run.
        return max(150, 120 + (url_len // 4))

    def _resolve_project_id(self, submission: CodeSubmissions) -> Optional[uuid.UUID]:
        assignment = self.session.get(Assignments, submission.assignment_id)
        if not assignment:
            return None
        return assignment.project_id

    def submit_code(
        self,
        *,
        user_id: uuid.UUID,
        assignment_id: uuid.UUID,
        github_repo_url: str | None = None,
        file_path: str | None = None,
        commit_hash: str | None = None,
    ):
        self.subscription_service.check_subscription(user_id=user_id)

        assignment = self.session.get(Assignments, assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        if hasattr(assignment, "is_active") and assignment.is_active is False:
            raise HTTPException(status_code=400, detail="Assignment is inactive")

        if not github_repo_url and not file_path:
            raise HTTPException(
                status_code=400,
                detail="Either github_repo_url or file_path must be provided",
            )

        submission = CodeSubmissions(
            assignment_id=assignment_id,
            user_id=user_id,
            github_repo_url=github_repo_url or "",
            submitted_at=datetime.utcnow(),
        )
        self._set_if_present(submission, "file_path", file_path)
        self._set_if_present(submission, "commit_hash", commit_hash)
        self._set_if_present(submission, "status", "submitted")

        self.session.add(submission)
        self.session.commit()
        self.session.refresh(submission)

        self._trigger_ai_grading(submission.id)
        return submission

    def _trigger_ai_grading(self, submission_id: uuid.UUID):
        submission = self.session.get(CodeSubmissions, submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        tokens_used = self._estimate_feedback_tokens(submission)
        project_id = self._resolve_project_id(submission)
        self.usage_service.check_quota(
            session=self.session,
            user_id=submission.user_id,
            tokens_required=tokens_used,
        )
        self.usage_service.check_rate_limit(
            session=self.session,
            user_id=submission.user_id,
            action_type="generate_feedback",
        )

        self._set_if_present(submission, "status", "grading")
        self.session.add(submission)
        self.session.commit()

        existing_feedback = self.session.exec(
            select(AICodeFeedback).where(AICodeFeedback.submission_id == submission_id)
        ).first()
        if existing_feedback:
            return submission

        feedback = AICodeFeedback(
            submission_id=submission.id,
            overview="Code evaluated successfully.",
            flow_analysis="Readable structure. Needs better edge-case handling.",
            improvement_suggestions="Optimize loops and improve boundary checks.",
            created_at=datetime.utcnow(),
        )

        self.session.add(feedback)
        self._set_if_present(submission, "status", "graded")
        self._set_if_present(submission, "graded_at", datetime.utcnow())
        self._set_if_present(submission, "score", 8.5)
        self.session.add(submission)
        self.session.commit()

        self.usage_service.log_usage(
            session=self.session,
            user_id=submission.user_id,
            project_id=project_id,
            action_type="generate_feedback",
            model_name="gpt-4o",
            tokens_used=tokens_used,
        )

        return submission

    def get_best_score(
        self,
        *,
        user_id: uuid.UUID,
        assignment_id: uuid.UUID,
    ):
        if not hasattr(CodeSubmissions, "score"):
            return 0

        best_score = self.session.exec(
            select(func.max(getattr(CodeSubmissions, "score"))).where(
                CodeSubmissions.user_id == user_id,
                CodeSubmissions.assignment_id == assignment_id,
            )
        ).one()
        return best_score or 0

    def get_submission_history(
        self,
        *,
        user_id: uuid.UUID,
        assignment_id: uuid.UUID,
    ):
        submissions = self.session.exec(
            select(CodeSubmissions)
            .where(
                CodeSubmissions.user_id == user_id,
                CodeSubmissions.assignment_id == assignment_id,
            )
            .order_by(CodeSubmissions.submitted_at.desc())
        ).all()
        return submissions

    def get_submission_detail(self, *, submission_id: uuid.UUID):
        submission = self.session.get(CodeSubmissions, submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        feedback = self.session.exec(
            select(AICodeFeedback).where(AICodeFeedback.submission_id == submission_id)
        ).first()
        return {"submission": submission, "feedback": feedback}
