import uuid
from fastapi import APIRouter, Depends, status

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.schemas.general import QueryParams
from app.models.schemas.users.user_schemas import (
    DeleteUser,
    UserCreate,
    UserMeUpdate,
    UserPublic,
    UserUpdate,
    UsersPublic,
)
from app.models.models import Users
from app.services.users import UserService

router = APIRouter()


@router.get("/me", response_model=UserPublic)
def get_current_user_profile(
    current_user: Users = Depends(Authen.get_current_user),
) -> UserPublic:
    return current_user


@router.patch("/me", response_model=UserPublic)
def update_current_user_profile(
    user_in: UserMeUpdate,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
) -> UserPublic:
    return UserService.update_current_user(
        session=session,
        user_id=current_user.id,
        user_in=user_in,
    )

@router.get(
    "",
    response_model=UsersPublic,
)
def get_users(
    session: SessionDep,
    query_params: QueryParams = Depends(),
    _: Users = Depends(Authen.require_admin),
) -> UsersPublic:
    return UserService.get_users(
        session=session,
        query_params=query_params,
    )


@router.get("/{user_id}", response_model=UserPublic)
def get_user_by_id(
    user_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.require_admin),
) -> UserPublic:
    return UserService.get_by_id(
        session=session,
        user_id=user_id,
    )


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    session: SessionDep,
    _: Users = Depends(Authen.require_admin),
) -> UserPublic:
    return UserService.create_user(
        session=session,
        user_in=user_in,
    )


@router.patch("/{user_id}", response_model=UserPublic)
def update_user(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    session: SessionDep,
    _: Users = Depends(Authen.require_admin),
) -> UserPublic:
    return UserService.update_user(
        session=session,
        user_id=user_id,
        user_in=user_in,
    )


@router.delete("/{user_id}", response_model=DeleteUser)
def delete_user(
    user_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.require_admin),
) -> DeleteUser:
    return UserService.delete_user(
        session=session,
        user_id=user_id,
    )
