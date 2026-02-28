import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.curriculum_Module import CurriculumModuleService

router = APIRouter()


class ModuleCreateBody(BaseModel):
    title: str
    description: str | None = None
    order_index: int | None = None


@router.post("/{curriculum_id}")
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
