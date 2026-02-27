import uuid
from fastapi import HTTPException
from sqlmodel import Session, select, func

from app.models.models import CurriculumModules, Curriculums


class CurriculumModuleService:

    def create_module(
        self,
        *,
        session: Session,
        curriculum_id: uuid.UUID,
        title: str,
        description: str | None = None,
        order_index: int | None = None
    ) -> CurriculumModules:

        curriculum = session.get(Curriculums, curriculum_id)
        if not curriculum:
            raise HTTPException(status_code=404, detail="Curriculum not found")

        if order_index is None:
            statement = (
                select(func.max(CurriculumModules.order_index))
                .where(CurriculumModules.curriculum_id == curriculum_id)
            )
            max_index = session.exec(statement).first()
            order_index = (max_index or 0) + 1

        module = CurriculumModules(
            curriculum_id=curriculum_id,
            title=title,
            description=description,
            order_index=order_index
        )

        session.add(module)
        session.commit()
        session.refresh(module)

        return module