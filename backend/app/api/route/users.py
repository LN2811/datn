import uuid
from fastapi import APIRouter, Depends, status

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.schemas.general import QueryParams
from app.models.schemas.users.user_schemas import (
    DeleteUser,
    UserCreate,
    UserPublic,
    UserUpdate,
    UsersPublic,
)
from app.services.users import UserService

router = APIRouter(
    dependencies=[Depends(Authen.require_admin)],
)

@router.get(
    "",
    response_model=UsersPublic,
)
def get_users(
    session: SessionDep,
    query_params: QueryParams = Depends(),
) -> UsersPublic:
    return UserService.get_users(
        session=session,
        query_params=query_params,
    )


@router.get("/{user_id}", response_model=UserPublic)
def get_user_by_id(user_id: uuid.UUID, session: SessionDep) -> UserPublic:
    return UserService.get_by_id(
        session=session,
        user_id=user_id,
    )


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(user_in: UserCreate, session: SessionDep) -> UserPublic:
    return UserService.create_user(
        session=session,
        user_in=user_in,
    )


@router.patch("/{user_id}", response_model=UserPublic)
def update_user(user_id: uuid.UUID, user_in: UserUpdate, session: SessionDep) -> UserPublic:
    return UserService.update_user(
        session=session,
        user_id=user_id,
        user_in=user_in,
    )


@router.delete("/{user_id}", response_model=DeleteUser)
def delete_user(user_id: uuid.UUID, session: SessionDep) -> DeleteUser:
    return UserService.delete_user(
        session=session,
        user_id=user_id,
    )
