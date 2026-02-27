import uuid
from typing import List

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.models import Criteria


class CriteriaService:
    def get_criteria(
        self,
        *,
        session: Session,
        criteria_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
    ) -> Criteria:
        criteria = session.get(Criteria, criteria_id)
        if not criteria:
            raise HTTPException(status_code=404, detail="Criteria not found")
        # project_id is accepted for backward compatibility; criteria are global in current model.
        return criteria

    def list_criteria(self, *, session: Session) -> List[Criteria]:
        return session.exec(select(Criteria).order_by(Criteria.name.asc())).all()
