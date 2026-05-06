import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.models.schemas.Curriculum_Module.curriculum_module_schemas import (
    CurriculumModulePublic,
)
from app.services.curriculum import CurriculumService

router = APIRouter()


class CurriculumCreateBody(BaseModel):
    project_id: uuid.UUID
    title: str
    overview: str | None = None
    generated_by: str = "ai"


class CurriculumUpdateBody(BaseModel):
    title: str | None = None
    overview: str | None = None
    generated_by: str | None = None
    is_active: bool | None = None


@router.post("")
def create_curriculum(
    curriculum_in: CurriculumCreateBody,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return CurriculumService().create_curriculum(
        session=session,
        curriculum_in=curriculum_in,
    )


@router.get("/project/{project_id}")
def get_curriculums_by_project(
    project_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return CurriculumService().get_curriculums_by_project(
        session=session,
        project_id=project_id,
    )


@router.get("/{curriculum_id}")
def get_curriculum_detail(
    curriculum_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return CurriculumService().get_curriculum_detail(
        session=session,
        curriculum_id=curriculum_id,
    )


@router.patch("/{curriculum_id}")
def update_curriculum(
    curriculum_id: uuid.UUID,
    curriculum_in: CurriculumUpdateBody,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return CurriculumService().update_curriculum(
        session=session,
        curriculum_id=curriculum_id,
        curriculum_in=curriculum_in,
    )


@router.delete("/{curriculum_id}")
def delete_curriculum(
    curriculum_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
) -> dict:
    return CurriculumService().delete_curriculum(
        session=session,
        curriculum_id=curriculum_id,
    )


@router.get(
    "/projects/{project_id}/lessons",
    response_model=list[CurriculumModulePublic],
)
def get_lessons_by_project(
    project_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
) -> list[CurriculumModulePublic]:
    return CurriculumService().get_lessons_by_curriculum(
        session=session,
        project_id=project_id,
    )


@router.post("/projects/{project_id}/generate-lessons")
@router.post("/projects/{project_id}/generate_lessions")
def generate_lessons_for_project(
    project_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
    force_regenerate: bool = False,
):
    return CurriculumService().generate_lessons_for_project(
        session=session,
        project_id=project_id,
        force_regenerate=force_regenerate,
    )
