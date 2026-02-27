import uuid
from fastapi import HTTPException
from sqlmodel import Session, select
from typing import List

from app.models.models import Curriculums, CurriculumModules, Projects
from app.models.schemas.curriculum_schemas import (
    CurriculumCreate,
    CurriculumUpdate
)


class CurriculumService:
    @staticmethod
    def _set_if_present(model_obj, field_name: str, value) -> None:
        if value is not None and hasattr(model_obj, field_name):
            setattr(model_obj, field_name, value)

    @staticmethod
    def _dump_payload(schema_obj) -> dict:
        if hasattr(schema_obj, "model_dump"):
            return schema_obj.model_dump(exclude_unset=True)
        if hasattr(schema_obj, "dict"):
            return schema_obj.dict(exclude_unset=True)
        return {}

    def create_curriculum(
        self,
        *,
        session: Session,
        curriculum_in: CurriculumCreate
    ) -> Curriculums:

        project = session.get(Projects, curriculum_in.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        curriculum = Curriculums(
            project_id=curriculum_in.project_id,
            title=curriculum_in.title,
            overview=curriculum_in.overview,
            generated_by=curriculum_in.generated_by,
        )

        session.add(curriculum)
        session.commit()
        session.refresh(curriculum)

        return curriculum


    def get_curriculums_by_project(
        self,
        *,
        session: Session,
        project_id: uuid.UUID
    ) -> List[Curriculums]:

        statement = (
            select(Curriculums)
            .where(Curriculums.project_id == project_id)
        )

        results = session.exec(statement).all()
        return results


    def get_curriculum_detail(
        self,
        *,
        session: Session,
        curriculum_id: uuid.UUID
    ) -> Curriculums:

        curriculum = session.get(Curriculums, curriculum_id)

        if not curriculum:
            raise HTTPException(status_code=404, detail="Curriculum not found")

        statement = (
            select(CurriculumModules)
            .where(CurriculumModules.curriculum_id == curriculum_id)
            .order_by(CurriculumModules.order_index)
        )

        modules = session.exec(statement).all()
        curriculum.modules = modules

        return curriculum


    def update_curriculum(
        self,
        *,
        session: Session,
        curriculum_id: uuid.UUID,
        curriculum_in: CurriculumUpdate
    ) -> Curriculums:

        curriculum = session.get(Curriculums, curriculum_id)

        if not curriculum:
            raise HTTPException(status_code=404, detail="Curriculum not found")

        update_data = self._dump_payload(curriculum_in)

        for key, value in update_data.items():
            if hasattr(curriculum, key):
                setattr(curriculum, key, value)

        session.add(curriculum)
        session.commit()
        session.refresh(curriculum)

        return curriculum


    def delete_curriculum(
        self,
        *,
        session: Session,
        curriculum_id: uuid.UUID
    ):

        curriculum = session.get(Curriculums, curriculum_id)

        if not curriculum:
            raise HTTPException(status_code=404, detail="Curriculum not found")

        if hasattr(curriculum, "is_active"):
            curriculum.is_active = False
            session.add(curriculum)
        else:
            session.delete(curriculum)
        session.commit()

        return {"message": "Curriculum deleted successfully"}
