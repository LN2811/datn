import uuid

from fastapi import APIRouter, Depends

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.assessment_Result import AssessmentResultService

router = APIRouter()


@router.post("/attempt/{attempt_id}")
def create_result_from_attempt(
    attempt_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return AssessmentResultService(session).create_from_attempt(attempt_id)
