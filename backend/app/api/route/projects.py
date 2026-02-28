import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.projects import ProjectService

router = APIRouter()


class ProjectCreateBody(BaseModel):
    name: str
    description: str | None = None


class ProjectUpdateBody(BaseModel):
    name: str | None = None
    description: str | None = None


@router.post("")
async def create_project(
    project_in: ProjectCreateBody,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
) -> dict:
    return await ProjectService().create_project(
        session=session,
        project_data=project_in,
        user_id=current_user.id,
    )


@router.patch("/{project_id}")
async def update_project(
    project_id: uuid.UUID,
    project_in: ProjectUpdateBody,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
) -> dict:
    return await ProjectService().update_project(
        session=session,
        project_id=project_id,
        project_data=project_in,
        user_id=current_user.id,
    )


@router.delete("/{project_id}")
async def delete_project(
    project_id: uuid.UUID,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
) -> dict:
    return await ProjectService().delete_project(
        session=session,
        project_id=project_id,
        user_id=current_user.id,
    )
