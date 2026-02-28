from fastapi import APIRouter, Depends

from app.authen.authen import Authen
from app.models.models import Users

router = APIRouter()

@router.get("/current-role")
def get_current_role(current_user: Users = Depends(Authen.get_current_user)) -> dict:
    return {
        "id": str(current_user.id),
        "role": ["admin"] if current_user.is_superuser else ["user"],
        "email": current_user.email,
    }
