import uuid
from fastapi import HTTPException
from sqlmodel import Session, select, func

from app.models.models import CurriculumModules, Curriculums, MaterialChunk
from app.services.text_cleaner import clean_vietnamese_text


class CurriculumModuleService:
    def get_module_detail(
        self,
        *,
        session: Session,
        module_id: uuid.UUID,
    ) -> CurriculumModules:
        module = session.get(CurriculumModules, module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        return module

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

        cleaned_title = clean_vietnamese_text(title).strip()
        cleaned_description = clean_vietnamese_text(description or "").strip()
        module = CurriculumModules(
            curriculum_id=curriculum_id,
            title=cleaned_title,
            description=cleaned_description or None,
            content=None,
            generate_status="pending",
            is_preview=False,
            order_index=order_index
        )

        session.add(module)
        curriculum.total_module = (curriculum.total_module or 0) + 1
        session.add(curriculum)
        session.commit()
        session.refresh(module)

        return module

    def delete_module(
        self,
        *,
        session: Session,
        module_id: uuid.UUID,
    ) -> dict:
        module = session.get(CurriculumModules, module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")

        curriculum = session.get(Curriculums, module.curriculum_id)
        material_chunks = session.exec(
            select(MaterialChunk).where(MaterialChunk.curriculum_module_id == module_id)
        ).all()
        for chunk in material_chunks:
            chunk.curriculum_module_id = None
            session.add(chunk)

        if curriculum:
            curriculum.total_module = max((curriculum.total_module or 1) - 1, 0)
            if module.generate_status == "ready" and module.content:
                curriculum.ready_module = max((curriculum.ready_module or 1) - 1, 0)
            session.add(curriculum)

        session.delete(module)
        session.commit()

        return {"id": str(module_id), "message": "Curriculum module deleted"}
