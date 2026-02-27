import uuid
from datetime import datetime
from sqlmodel import Session, select
from fastapi import HTTPException

from app.models.models import (
    Criteria,
    AssessmentAttempt,
    Answers,
    AssessmentResults,
    Questions,
)


class AssessmentResultService:

    def __init__(self, session: Session):
        self.session = session

    def _calculate_readiness(self, total_score: float) -> str:
        if total_score > 80:
            return "high"
        elif total_score >= 50:
            return "medium"
        return "low"

    def _calculate_weighted_score(self, answers: list[Answers]) -> float:
        question_ids = [answer.question_id for answer in answers]
        if not question_ids:
            return 0.0

        rows = self.session.exec(
            select(Questions.id, Criteria.weight)
            .join(Criteria, Questions.criteria_id == Criteria.id)
            .where(Questions.id.in_(question_ids))
        ).all()

        weight_map: dict[uuid.UUID, float] = {
            question_id: float(weight) if weight is not None else 1.0
            for question_id, weight in rows
        }

        weighted_score = 0.0
        max_weighted_score = 0.0
        for answer in answers:
            weight = weight_map.get(answer.question_id, 1.0)
            score = float(answer.score or 0)
            weighted_score += score * weight
            max_weighted_score += 5.0 * weight

        if max_weighted_score <= 0:
            return 0.0

        return round((weighted_score / max_weighted_score) * 100.0, 2)

    def create_from_attempt(self, attempt_id: uuid.UUID):

        attempt = self.session.get(AssessmentAttempt, attempt_id)
        if not attempt:
            raise HTTPException(status_code=404, detail="Attempt not found")

        existing = self.session.exec(
            select(AssessmentResults).where(
                AssessmentResults.user_id == attempt.user_id,
                AssessmentResults.project_id == attempt.project_id
            )
            .order_by(AssessmentResults.created_at.desc())
        ).first()

        answers = self.session.exec(
            select(Answers).where(Answers.attempt_id == attempt_id)
        ).all()

        if not answers:
            raise HTTPException(status_code=400, detail="No answers found")

        total_score = self._calculate_weighted_score(answers)

        level = self._calculate_readiness(total_score)

        if existing and attempt.is_submitted:
            # Avoid creating duplicate "latest" results for the same submitted attempt.
            if abs((datetime.utcnow() - existing.created_at).total_seconds()) < 10:
                return existing

        result = AssessmentResults(
            user_id=attempt.user_id,
            project_id=attempt.project_id,
            total_score=total_score,
            readiness_level=level,
            created_at=datetime.utcnow()
        )

        self.session.add(result)
        self.session.commit()
        self.session.refresh(result)

        # Auto-generate AI analysis for each newly created result.
        from app.services.ai_analysis import AIAnalysisService
        try:
            AIAnalysisService(self.session).generate(result.id)
        except HTTPException as exc:
            # Keep result creation successful even if AI quota/rate limit is hit.
            if exc.status_code not in {403, 429}:
                raise

        return result
