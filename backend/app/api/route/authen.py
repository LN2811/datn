from fastapi import APIRouter, Depends

from app.authen.authen import Authen
from app.models.models import Users

router = APIRouter()


@router.get("/current-user")
def get_current_user(current_user: Users = Depends(Authen.get_current_user)) -> dict:
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "account_name": current_user.account_name,
        "contact_email": current_user.contact_email,
        "contact_phone": current_user.contact_phone,
        "avatar_url": current_user.avatar_url,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
    }


@router.get("/current-role")
def get_current_role(current_user: Users = Depends(Authen.get_current_user)) -> dict:
    return {
        "id": str(current_user.id),
        "role": ["admin"] if current_user.is_superuser else ["user"],
        "email": current_user.email,
    }
