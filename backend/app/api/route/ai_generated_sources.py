import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.ai_Generated_Source import AIGeneratedSourceService

router = APIRouter()


class SourceCreateBody(BaseModel):
    project_id: uuid.UUID
    source_url: str | None = None
    title: str | None = None
    content_summary: str | None = None
    source_type: str = "web"


class SourceUpdateBody(BaseModel):
    source_url: str | None = None
    title: str | None = None
    content_summary: str | None = None
    source_type: str | None = None


@router.post("")
def create_source(
    payload: SourceCreateBody,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return AIGeneratedSourceService().create(
        session=session,
        project_id=payload.project_id,
        source_url=payload.source_url,
        title=payload.title,
        content_summary=payload.content_summary,
        source_type=payload.source_type,
    )


@router.get("/project/{project_id}")
def get_sources_by_project(
    project_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return AIGeneratedSourceService().get_by_project(
        session=session,
        project_id=project_id,
    )


@router.get("/project/{project_id}/search")
def search_sources(
    project_id: uuid.UUID,
    keyword: str,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return AIGeneratedSourceService().search(
        session=session,
        project_id=project_id,
        keyword=keyword,
    )


@router.get("/project/{project_id}/stats")
def source_stats(
    project_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return AIGeneratedSourceService().stats(
        session=session,
        project_id=project_id,
    )


@router.get("/{source_id}")
def get_source_by_id(
    source_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return AIGeneratedSourceService().get_by_id(
        session=session,
        source_id=source_id,
    )


@router.patch("/{source_id}")
def update_source(
    source_id: uuid.UUID,
    payload: SourceUpdateBody,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return AIGeneratedSourceService().update(
        session=session,
        source_id=source_id,
        source_url=payload.source_url,
        title=payload.title,
        content_summary=payload.content_summary,
        source_type=payload.source_type,
    )


@router.delete("/{source_id}")
def delete_source(
    source_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
) -> dict:
    return AIGeneratedSourceService().delete(
        session=session,
        source_id=source_id,
    )
