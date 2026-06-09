import uuid
import logging
from typing import Any, List

from fastapi import HTTPException, UploadFile
from sqlmodel import Session, select

from app.models.models import LearningMaterials, Projects, Users
from app.services.material_chunk import MaterialChunkService
from app.services.storage import save_uploaded_file

logger = logging.getLogger("uvicorn.error")


class LearningMaterialService:
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _dump_payload(schema_obj: Any) -> dict:
        if hasattr(schema_obj, "model_dump"):
            return schema_obj.model_dump(exclude_unset=True)
        if hasattr(schema_obj, "dict"):
            return schema_obj.dict(exclude_unset=True)
        return {}

    def create_material(
        self,
        *,
        project_id: uuid.UUID,
        title: str,
        external_link: str | None = None,
        file_path: UploadFile | None = None,
        current_user: Users,
    ) -> LearningMaterials:
        project = self.session.get(Projects, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if file_path and external_link:
            raise HTTPException(
                status_code=400,
                detail="Provide either file_path or external_link, not both",
            )
        if not file_path and not external_link:
            raise HTTPException(
                status_code=400,
                detail="Either file_path or external_link must be provided",
            )

        saved_file_path = None
        if file_path:
            file_info = save_uploaded_file(file_path)
            saved_file_path = file_info["file_path"]

        material = LearningMaterials(
            project_id=project_id,
            title=title,
            file_path=saved_file_path,
            external_link=external_link,
            uploaded_by=current_user.id,
        )
        self.session.add(material)
        self.session.commit()
        self.session.refresh(material)

        try:
            MaterialChunkService(self.session).save_material_chunk(
                material_id=material.id,
            )
        except HTTPException:
            self.session.delete(material)
            self.session.commit()
            raise
        except Exception as exc:
            logger.warning(
                "Failed to create material chunks. material_id=%s error_type=%s error=%s",
                material.id,
                type(exc).__name__,
                exc,
            )

        return material


    def get_materials_by_project(
        self,
        *,
        project_id: uuid.UUID,
    ) -> List[LearningMaterials]:
        project = self.session.get(Projects, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        statement = select(LearningMaterials).where(LearningMaterials.project_id == project_id)
        if hasattr(LearningMaterials, "is_active"):
            statement = statement.where(getattr(LearningMaterials, "is_active") == True)
        return self.session.exec(statement).all()

    def get_material_detail(
        self,
        *,
        material_id: uuid.UUID,
    ) -> LearningMaterials:
        material = self.session.get(LearningMaterials, material_id)
        if not material:
            raise HTTPException(status_code=404, detail="Learning material not found")
        if hasattr(material, "is_active") and material.is_active is False:
            raise HTTPException(status_code=404, detail="Learning material not found")
        return material

    def update_material(
        self,
        *,
        material_id: uuid.UUID,
        material_in: Any,
    ) -> LearningMaterials:
        material = self.session.get(LearningMaterials, material_id)
        if not material:
            raise HTTPException(status_code=404, detail="Learning material not found")
        if hasattr(material, "is_active") and material.is_active is False:
            raise HTTPException(status_code=404, detail="Learning material not found")

        update_data = self._dump_payload(material_in)
        if "url" in update_data and "external_link" not in update_data:
            update_data["external_link"] = update_data.pop("url")

        if "file_path" in update_data and "external_link" in update_data:
            file_path = update_data.get("file_path")
            external_link = update_data.get("external_link")
            if file_path and external_link:
                raise HTTPException(
                    status_code=400,
                    detail="Provide either file_path or external_link, not both",
                )

        for key, value in update_data.items():
            if hasattr(material, key):
                setattr(material, key, value)

        self.session.add(material)
        self.session.commit()
        self.session.refresh(material)
        return material

    def delete_material(
        self,
        *,
        material_id: uuid.UUID,
    ) -> None:
        material = self.session.get(LearningMaterials, material_id)
        if not material:
            raise HTTPException(status_code=404, detail="Learning material not found")
        if hasattr(material, "is_active"):
            material.is_active = False
            self.session.add(material)
        else:
            self.session.delete(material)
        self.session.commit()
