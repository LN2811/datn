import uuid

from fastapi import APIRouter, Depends

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.criteria import CriteriaService

router = APIRouter()


@router.get("")
def list_criteria(
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return CriteriaService().list_criteria(session=session)


@router.get("/{criteria_id}")
def get_criteria(
    criteria_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return CriteriaService().get_criteria(
        session=session,
        criteria_id=criteria_id,
    )
