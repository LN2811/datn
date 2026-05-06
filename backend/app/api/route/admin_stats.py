from fastapi import APIRouter, Depends

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.admin_stats import AdminStatsService

router = APIRouter()


@router.get("/stats")
def get_admin_stats(
    session: SessionDep,
    year: int | None = None,
    _: Users = Depends(Authen.require_admin),
) -> dict:
    return AdminStatsService(session).dashboard(year=year)
