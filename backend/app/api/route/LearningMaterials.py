import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.LearningMaterials import LearningMaterialService

router = APIRouter()


class LearningMaterialCreateBody(BaseModel):
    uploaded_by: uuid.UUID
    title: str
    file_path: str | None = None
    external_link: str | None = None
    url: str | None = None


class LearningMaterialUpdateBody(BaseModel):
    title: str | None = None
    file_path: str | None = None
    external_link: str | None = None
    url: str | None = None


@router.post("/project/{project_id}")
def create_material(
    project_id: uuid.UUID,
    material_in: LearningMaterialCreateBody,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return LearningMaterialService(session).create_material(
        project_id=project_id,
        material_in=material_in,
    )


@router.get("/project/{project_id}")
def get_materials_by_project(
    project_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return LearningMaterialService(session).get_materials_by_project(
        project_id=project_id,
    )


@router.get("/{material_id}")
def get_material_detail(
    material_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return LearningMaterialService(session).get_material_detail(
        material_id=material_id,
    )


@router.patch("/{material_id}")
def update_material(
    material_id: uuid.UUID,
    material_in: LearningMaterialUpdateBody,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return LearningMaterialService(session).update_material(
        material_id=material_id,
        material_in=material_in,
    )


@router.delete("/{material_id}")
def delete_material(
    material_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
) -> dict:
    LearningMaterialService(session).delete_material(
        material_id=material_id,
    )
    return {"id": str(material_id), "message": "Learning material deleted"}
