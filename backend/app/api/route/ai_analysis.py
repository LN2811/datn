import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.ai_analysis import AIAnalysisService

router = APIRouter()


class GenerateAnalysisBody(BaseModel):
    model_name: str = "gpt-4o"
    tokens_used: int = 180


@router.post("/results/{result_id}/generate")
def generate_analysis(
    result_id: uuid.UUID,
    payload: GenerateAnalysisBody,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return AIAnalysisService(session).generate(
        result_id,
        model_name=payload.model_name,
        tokens_used=payload.tokens_used,
    )
