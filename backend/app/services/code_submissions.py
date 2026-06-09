import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import update
from sqlmodel import Session, func, select

from app.models.models import AICodeFeedback, Assignments, CodeSubmissions
from app.services.Ai_code_feedback import AICodeFeedbackService
from app.services.ai_transaction import AITransactionService
from app.services.context_selector import CODE_REVIEW, ContextSelector
from app.services.github_code_reader import GithubCodeReader
from app.services.user_subscriptions import UserSubscriptionService


CODE_REVIEW_COMPLETION_TOKENS = 1200
logger = logging.getLogger("uvicorn.error")


class CodeSubmissionService:
    def __init__(self, session: Session):
        self.session = session
        self.subscription_service = UserSubscriptionService(session)

    @staticmethod
    def _set_if_present(model_obj, field_name: str, value) -> None:
        if value is not None and hasattr(model_obj, field_name):
            setattr(model_obj, field_name, value)

    @staticmethod
    def _estimate_feedback_tokens(_: CodeSubmissions) -> int:
        return CODE_REVIEW_COMPLETION_TOKENS

    def _resolve_project_id(self, submission: CodeSubmissions) -> Optional[uuid.UUID]:
        assignment = self.session.get(Assignments, submission.assignment_id)
        if not assignment:
            return None
        return assignment.project_id

    def _sync_submission_from_feedback(
        self,
        *,
        submission: CodeSubmissions,
        feedback: AICodeFeedback | None,
        commit: bool = True,
    ) -> CodeSubmissions:
        if not feedback:
            return submission

        feedback_changed = AICodeFeedbackService.normalize_feedback_record(feedback)
        if feedback_changed:
            self.session.add(feedback)

        AICodeFeedbackService._mark_submission_graded(
            session=self.session,
            submission=submission,
            code_quality_score=getattr(feedback, "code_quality_score", None),
            logic_score=getattr(feedback, "logic_score", None),
            performance_score=getattr(feedback, "performance_score", None),
        )
        if commit:
            self.session.commit()
            self.session.refresh(submission)
            if feedback is not None:
                self.session.refresh(feedback)
        return submission

    @staticmethod
    def _feedback_to_dict(feedback: AICodeFeedback | None) -> dict[str, Any] | None:
        if not feedback:
            return None

        AICodeFeedbackService.normalize_feedback_record(feedback)
        return {
            "id": str(feedback.id),
            "submission_id": str(feedback.submission_id),
            "overview": feedback.overview,
            "flow_analysis": feedback.flow_analysis,
            "code_quality_score": feedback.code_quality_score,
            "logic_score": feedback.logic_score,
            "performance_score": feedback.performance_score,
            "strengths": feedback.strengths,
            "weaknesses": feedback.weaknesses,
            "improvement_suggestions": feedback.improvement_suggestions,
            "generated_by": getattr(feedback, "generated_by", None),
            "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
        }

    @classmethod
    def _submission_to_dict(
        cls,
        submission: CodeSubmissions,
        feedback: AICodeFeedback | None = None,
    ) -> dict[str, Any]:
        return {
            "id": str(submission.id),
            "assignment_id": str(submission.assignment_id),
            "user_id": str(submission.user_id),
            "github_repo_url": submission.github_repo_url,
            "file_path": getattr(submission, "file_path", None),
            "commit_hash": getattr(submission, "commit_hash", None),
            "score": getattr(submission, "score", None),
            "status": getattr(submission, "status", None),
            "submitted_at": (
                submission.submitted_at.isoformat()
                if getattr(submission, "submitted_at", None)
                else None
            ),
            "graded_at": (
                submission.graded_at.isoformat()
                if getattr(submission, "graded_at", None)
                else None
            ),
            "feedback": cls._feedback_to_dict(feedback),
        }

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

        if github_repo_url:
            try:
                self._trigger_ai_grading(submission.id)
            except HTTPException as exc:
                logger.warning(
                    "Code submission saved but grading failed. submission_id=%s "
                    "status_code=%s detail=%s",
                    submission.id,
                    exc.status_code,
                    exc.detail,
                )
                self.session.refresh(submission)
            except Exception as exc:
                logger.warning(
                    "Code submission saved but grading failed. submission_id=%s "
                    "error_type=%s error=%s",
                    submission.id,
                    type(exc).__name__,
                    exc,
                )
                self.session.refresh(submission)
        return submission

    def _trigger_ai_grading(self, submission_id: uuid.UUID, *, force: bool = False):
        submission = self.session.get(CodeSubmissions, submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        assignment = self.session.get(Assignments, submission.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        existing_feedback = self.session.exec(
            select(AICodeFeedback).where(AICodeFeedback.submission_id == submission_id)
        ).first()
        if existing_feedback:
            if not force:
                self._sync_submission_from_feedback(
                    submission=submission,
                    feedback=existing_feedback,
                )
                return submission

            self.session.delete(existing_feedback)
            self._set_if_present(submission, "score", None)
            self._set_if_present(submission, "graded_at", None)
            self._set_if_present(submission, "status", "submitted")
            self.session.add(submission)
            self.session.commit()
            self.session.refresh(submission)
        if getattr(submission, "status", None) == "grading" and not force:
            return submission

        github_repo_url = submission.github_repo_url
        if not github_repo_url:
            raise HTTPException(
                status_code=400,
                detail="No GitHub repository URL provided for grading",
            )

        if force and getattr(submission, "status", None) == "grading":
            self._set_if_present(submission, "status", "submitted")
            self.session.add(submission)
            self.session.commit()
            self.session.refresh(submission)

        claim_result = self.session.exec(
            update(CodeSubmissions)
            .where(
                CodeSubmissions.id == submission.id,
                CodeSubmissions.status != "grading",
            )
            .values(status="grading")
        )
        self.session.commit()
        if claim_result.rowcount != 1:
            self.session.refresh(submission)
            return submission
        self.session.refresh(submission)

        try:
            code_snapshot = GithubCodeReader.read_code_repo(
                github_repo_url,
                ref=getattr(submission, "commit_hash", None),
            )
            self._set_if_present(
                submission,
                "commit_hash",
                code_snapshot.commit_hash,
            )
            self.session.add(submission)
            self.session.commit()
            self.session.refresh(submission)

            review_context = ContextSelector(self.session).select(
                CODE_REVIEW,
                assignment.project_id,
                assignment=assignment,
                source_code=code_snapshot.combined_content,
                rubric=getattr(assignment, "grading_rubric", None),
                expected_outcomes=getattr(assignment, "expected_outcomes", None),
            )
            prompt = self._build_code_review_prompt(
                assignment=assignment,
                repo_url=code_snapshot.repo_url,
                branch=code_snapshot.branch,
                commit_hash=code_snapshot.commit_hash,
                combined_content=review_context.text,
            )
            ai_response = AITransactionService.chat(
                db=self.session,
                user_id=submission.user_id,
                project_id=assignment.project_id,
                action_type="code_review",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Bạn là trợ giảng AI chuyên đánh giá chất lượng code sinh viên nộp. "
                            "Luôn viết toàn bộ nhận xét bằng tiếng Việt có dấu tự nhiên. "
                            "Chỉ trả về JSON hợp lệ, không markdown, không giải thích thêm bên ngoài JSON."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_completion_tokens=self._estimate_feedback_tokens(submission),
                context_selection=review_context,
            )

            feedback_payload = self._parse_github_response(ai_response)
            score_fields = self._normalize_score_fields(feedback_payload)
            AICodeFeedbackService().create(
                session=self.session,
                submission_id=submission.id,
                overview=str(feedback_payload.get("overview") or "").strip()
                or "AI chưa trả về nhận xét tổng quan.",
                flow_analysis=self._string_or_none(feedback_payload.get("flow_analysis")),
                improvement_suggestions=self._string_or_none(
                    feedback_payload.get("improvement_suggestions")
                ),
                code_quality_score=score_fields["code_quality_score"],
                logic_score=score_fields["logic_score"],
                performance_score=score_fields["performance_score"],
                strengths=self._string_or_none(feedback_payload.get("strengths")),
                weaknesses=self._string_or_none(feedback_payload.get("weaknesses")),
                generated_by="ai",
                track_usage=False,
            )
            self.session.refresh(submission)
            return submission
        except HTTPException:
            self._set_if_present(submission, "status", "failed")
            self.session.add(submission)
            self.session.commit()
            self.session.refresh(submission)
            raise
        except Exception as exc:
            self._set_if_present(submission, "status", "failed")
            self.session.add(submission)
            self.session.commit()
            self.session.refresh(submission)
            raise HTTPException(status_code=500, detail=f"Error during AI grading: {exc}") from exc

    def retry_ai_grading(
        self,
        *,
        submission_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superuser: bool = False,
    ):
        submission = self.session.get(CodeSubmissions, submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        if submission.user_id != user_id and not is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized")

        self._trigger_ai_grading(submission_id, force=True)
        return self.get_submission_detail(submission_id=submission_id)

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
        has_updates = False
        feedback_by_submission_id: dict[uuid.UUID, AICodeFeedback | None] = {}
        for submission in submissions:
            feedback = self.session.exec(
                select(AICodeFeedback).where(AICodeFeedback.submission_id == submission.id)
            ).first()
            feedback_by_submission_id[submission.id] = feedback
            previous_status = getattr(submission, "status", None)
            previous_score = getattr(submission, "score", None)
            self._sync_submission_from_feedback(
                submission=submission,
                feedback=feedback,
                commit=False,
            )
            if (
                getattr(submission, "status", None) != previous_status
                or getattr(submission, "score", None) != previous_score
            ):
                has_updates = True

        if has_updates:
            self.session.commit()
            for submission in submissions:
                self.session.refresh(submission)
            for feedback in feedback_by_submission_id.values():
                if feedback is not None:
                    self.session.refresh(feedback)

        return [
            self._submission_to_dict(
                submission,
                feedback_by_submission_id.get(submission.id),
            )
            for submission in submissions
        ]

    def get_submission_detail(self, *, submission_id: uuid.UUID):
        submission = self.session.get(CodeSubmissions, submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        feedback = self.session.exec(
            select(AICodeFeedback).where(AICodeFeedback.submission_id == submission_id)
        ).first()
        self._sync_submission_from_feedback(
            submission=submission,
            feedback=feedback,
        )
        return self._submission_to_dict(submission, feedback)

    @staticmethod
    def _extract_github_info(content: str) -> str:
        cleaned = (content or "").strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        if cleaned.startswith("{") and cleaned.endswith("}"):
            return cleaned

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end > start:
            return cleaned[start : end + 1]
        return cleaned

    @staticmethod
    def _parse_github_response(content: str) -> dict[str, Any]:
        try:
            data = json.loads(CodeSubmissionService._extract_github_info(content))
        except Exception:
            return {
                "overview": content.strip()
                or "AI đã phân tích bài làm nhưng không trả về JSON hợp lệ.",
                "code_quality_score": None,
                "logic_score": None,
                "performance_score": None,
                "strengths": None,
                "weaknesses": None,
                "improvement_suggestions": "Vui lòng kiểm tra lại source code và prompt chấm bài.",
                "flow_analysis": None,
            }

        if not isinstance(data, dict):
            raise HTTPException(status_code=500, detail="AI response is not a valid JSON object")

        if "code_quality_score" not in data and "Code_quality_score" in data:
            data["code_quality_score"] = data.get("Code_quality_score")

        return data

    @classmethod
    def _normalize_score_fields(cls, payload: dict[str, Any]) -> dict[str, float | None]:
        scores = {
            "code_quality_score": cls._to_float_or_none(
                payload.get("code_quality_score")
            ),
            "logic_score": cls._to_float_or_none(payload.get("logic_score")),
            "performance_score": cls._to_float_or_none(
                payload.get("performance_score")
            ),
        }
        overall_score = cls._to_float_or_none(payload.get("overall_score"))
        if overall_score is None:
            return scores

        return {
            key: value if value is not None else overall_score
            for key, value in scores.items()
        }

    @staticmethod
    def _to_float_or_none(value: Any) -> float | None:
        if value is None:
            return None
        try:
            score = float(value)
        except (TypeError, ValueError):
            return None
        return max(0.0, min(10.0, score))

    @staticmethod
    def _string_or_none(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, list):
            return "\n".join(str(item) for item in value if item is not None).strip() or None
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False)
        return str(value).strip() or None

    @staticmethod
    def _build_code_review_prompt(
        *,
        assignment: Assignments,
        repo_url: str,
        branch: str,
        commit_hash: str | None,
        combined_content: str,
    ) -> str:
        return f"""
Hãy review source code sinh viên nộp từ GitHub.
Viết toàn bộ nội dung phản hồi bằng tiếng Việt có dấu, tự nhiên và dễ hiểu.
Không dùng tiếng Anh trong các trường nhận xét, trừ tên hàm, tên biến, thư viện, framework hoặc thuật ngữ kỹ thuật bắt buộc.

Thông tin bài tập:
- Tiêu đề: {assignment.title}
- Mô tả: {assignment.description or ""}

Thông tin repository:
- URL: {repo_url}
- Nhánh/ref: {branch}
- Commit: {commit_hash or "N/A"}

Yêu cầu đánh giá:
- Nhận xét tổng quan về bài làm, trả vào key "overview"
- Phân tích luồng xử lý chính, trả vào key "flow_analysis"
- Điểm chất lượng code từ 0 đến 10, trả vào key "code_quality_score"
- Điểm logic từ 0 đến 10, trả vào key "logic_score"
- Điểm hiệu năng từ 0 đến 10, trả vào key "performance_score"
- Điểm mạnh của code, trả vào key "strengths"
- Điểm yếu của code, trả vào key "weaknesses"
- Gợi ý cải thiện cụ thể, trả vào key "improvement_suggestions"
- Tất cả giá trị dạng text trong JSON phải là tiếng Việt có dấu.

Chỉ trả về đúng một JSON object theo cấu trúc sau:
{{
    "overview": "Nhận xét tổng quan về chất lượng code",
    "code_quality_score": 8.5,
    "logic_score": 8.0,
    "performance_score": 7.5,
    "strengths": "Những điểm mạnh của code",
    "weaknesses": "Những điểm yếu của code",
    "improvement_suggestions": "Các gợi ý cải thiện cụ thể",
    "flow_analysis": "Phân tích luồng xử lý chính của code",
    "overall_score": 8.0
}}

Source code cần đánh giá:
```text
{combined_content}
```
"""
