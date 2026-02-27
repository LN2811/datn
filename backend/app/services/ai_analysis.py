import uuid
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.models import AIAnalysis, AssessmentResults
from app.services.ai_Usage_Log import AIUsageService


class AIAnalysisService:

    DEFAULT_MODEL_NAME = "gpt-4o"
    DEFAULT_TOKENS_USED = 180

    def __init__(self, session: Session):
        self.session = session
        self.usage_service = AIUsageService()

    @staticmethod
    def _build_payload(result: AssessmentResults) -> dict[str, Any]:
        total_score = result.total_score or 0
        level = result.readiness_level

        if level == "high":
            strengths = "Strong fundamentals and strong readiness to start implementation."
            weaknesses = "Minor risks around edge-case validation and long-term maintainability."
            recommendations = "Ship incrementally and add deeper test coverage for edge cases."
        elif level == "medium":
            strengths = "Solid baseline understanding of core concepts."
            weaknesses = "Inconsistent depth across criteria and weak spots in practical application."
            recommendations = "Prioritize weaker criteria and practice with production-like tasks."
        else:
            strengths = "Basic awareness is present and can be improved with guided practice."
            weaknesses = "Foundational gaps across multiple criteria reduce delivery readiness."
            recommendations = "Focus on fundamentals first, then re-assess after targeted exercises."

        return {
            "analysis_text": f"User scored {total_score} with readiness level {level}.",
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommendations": recommendations,
            "generated_by": "ai",
        }

    def generate(
        self,
        result_id: uuid.UUID,
        *,
        model_name: str = DEFAULT_MODEL_NAME,
        tokens_used: int = DEFAULT_TOKENS_USED,
    ):

        result = self.session.get(AssessmentResults, result_id)
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Assessment result not found",
            )

        safe_tokens = max(tokens_used, 1)
        self.usage_service.check_quota(
            session=self.session,
            user_id=result.user_id,
            tokens_required=safe_tokens,
        )
        self.usage_service.check_rate_limit(
            session=self.session,
            user_id=result.user_id,
            action_type="generate_analysis",
        )

        payload = self._build_payload(result)
        existing = self.session.exec(
            select(AIAnalysis)
            .where(AIAnalysis.assessment_result_id == result_id)
        ).first()

        if existing:
            updated = False
            for key, value in payload.items():
                if hasattr(existing, key) and getattr(existing, key) != value:
                    setattr(existing, key, value)
                    updated = True

            if updated:
                self.session.add(existing)
                self.session.commit()
                self.session.refresh(existing)

            self.usage_service.log_usage(
                session=self.session,
                user_id=result.user_id,
                project_id=result.project_id,
                action_type="generate_analysis",
                model_name=model_name,
                tokens_used=safe_tokens,
            )
            return existing

        analysis = AIAnalysis(
            assessment_result_id=result.id,
            **payload,
        )

        self.session.add(analysis)
        self.session.commit()
        self.session.refresh(analysis)

        self.usage_service.log_usage(
            session=self.session,
            user_id=result.user_id,
            project_id=result.project_id,
            action_type="generate_analysis",
            model_name=model_name,
            tokens_used=safe_tokens,
        )

        return analysis
