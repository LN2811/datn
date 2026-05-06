import uuid
import logging
from typing import List

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.models import Curriculums, CurriculumModules, LearningMaterials, Projects
from app.models.schemas.Curriculums.curriculum_schemas import (
    CurriculumCreate,
    CurriculumUpdate,
)
from app.services.file_parser import extract_text
from app.services.ai_service import call_lln
from app.services.text_cleaner import clean_vietnamese_text

logger = logging.getLogger("uvicorn.error")


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
            title=clean_vietnamese_text(curriculum_in.title).strip(),
            overview=clean_vietnamese_text(curriculum_in.overview or "").strip() or None,
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
                if key in {"title", "overview"} and value is not None:
                    value = clean_vietnamese_text(str(value)).strip()
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

    def get_lessons_by_curriculum(
        self,
        *,
        session: Session,
        project_id: uuid.UUID,
    ) -> List[CurriculumModules]:
        latest_curriculum = session.exec(
            select(Curriculums)
            .where(Curriculums.project_id == project_id)
            .order_by(Curriculums.created_at.desc())
        ).first()

        if not latest_curriculum:
            return []

        statement = (
            select(CurriculumModules)
            .where(CurriculumModules.curriculum_id == latest_curriculum.id)
            .order_by(CurriculumModules.order_index, CurriculumModules.created_at)
        )

        return session.exec(statement).all()

    @staticmethod
    def _build_module_description(module_data: dict, index: int) -> str:
        description = module_data.get("description") or module_data.get("content")
        if isinstance(description, str) and description.strip():
            return description.strip()

        lessons = module_data.get("lessons")
        if isinstance(lessons, list):
            lines: list[str] = []
            for lesson_index, lesson in enumerate(lessons, start=1):
                if not isinstance(lesson, dict):
                    continue

                lesson_title = str(
                    lesson.get("title") or f"Lesson {lesson_index}"
                ).strip()
                lesson_content = str(
                    lesson.get("content") or lesson.get("description") or ""
                ).strip()

                if lesson_content:
                    lines.append(f"{lesson_title}: {lesson_content}")
                else:
                    lines.append(lesson_title)

            if lines:
                return "\n".join(lines)

        return f"Module {index}"

    def generate_lessons_for_project(
        self,
        *,
        session: Session,
        project_id: uuid.UUID,
        force_regenerate: bool = False,
    ) -> dict:
        from app.services.curriculum_generate import CurriculumGenerationService

        return CurriculumGenerationService().generate_from_curriculum(
            session=session,
            project_id=project_id,
            force_regenerate=force_regenerate,
        )

    def generate_curriculum(
        self,
        *,
        session: Session,
        project_id: uuid.UUID,
        generated_by: uuid.UUID,
    ) -> dict:
        del generated_by
        return self.generate_lessons_for_project(
            session=session,
            project_id=project_id,
        )

    def generate_lessions(
        self,
        session: Session,
        project_id,
        user_id,
    ) -> dict:
        del user_id
        return self.generate_lessons_for_project(
            session=session,
            project_id=project_id,
        )
