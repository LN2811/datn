import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.models.schemas.Curriculum_Module.curriculum_module_schemas import (
    CurriculumModulePublic,
)
from app.services.ai_service import ai_usage_tracking_context
from app.services.curriculum_Module import CurriculumModuleService
from app.services.curriculum_generate import CurriculumGenerationService

router = APIRouter()


class ModuleCreateBody(BaseModel):
    title: str
    description: str | None = None
    order_index: int | None = None


@router.post("/{curriculum_id}", response_model=CurriculumModulePublic)
def create_module(
    curriculum_id: uuid.UUID,
    module_in: ModuleCreateBody,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return CurriculumModuleService().create_module(
        session=session,
        curriculum_id=curriculum_id,
        title=module_in.title,
        description=module_in.description,
        order_index=module_in.order_index,
    )


@router.get("/module/{module_id}", response_model=CurriculumModulePublic)
def get_module_detail(
    module_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return CurriculumModuleService().get_module_detail(
        session=session,
        module_id=module_id,
    )


@router.delete("/module/{module_id}")
def delete_module(
    module_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
) -> dict:
    return CurriculumModuleService().delete_module(
        session=session,
        module_id=module_id,
    )


@router.post("/module/{module_id}/ensure-ready", response_model=CurriculumModulePublic)
def ensure_module_ready(
    module_id: uuid.UUID,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
):
    service = CurriculumGenerationService()
    with ai_usage_tracking_context(
        session=session,
        user_id=current_user.id,
        action_type="generate_lesson",
    ):
        module = service.ensure_module_ready(
            session=session,
            module_id=module_id,
        )
    return module


@router.post("/module/{module_id}/prefetch-next")
def prefetch_next_modules(
    module_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: Users = Depends(Authen.get_current_user),
) -> dict:
    service = CurriculumGenerationService()
    background_tasks.add_task(
        service.prefetch_next_modules_background,
        module_id=module_id,
        limit=2,
        user_id=current_user.id,
    )
    return {"message": "Prefetch scheduled"}
