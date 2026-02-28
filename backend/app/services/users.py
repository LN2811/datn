import uuid
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session, asc, desc, func, or_, select

from app.core.sercurity import get_password_hash
from app.models.schemas.general import QueryParams
from app.models.models import Users


class UserService:
    ALLOWED_SORT_FIELDS = {"id", "email", "is_active", "is_superuser"}

    @staticmethod
    def _dump_payload(schema_obj: Any) -> dict:
        if hasattr(schema_obj, "model_dump"):
            return schema_obj.model_dump(exclude_unset=True)
        if hasattr(schema_obj, "dict"):
            return schema_obj.dict(exclude_unset=True)
        return {}

    @staticmethod
    def get_users(
        *,
        session: Session,
        query_params: QueryParams,
    ) -> dict:
        page_size = query_params.page_size
        page_index = query_params.page_index
        sort_by = query_params.sort_by or "email"
        sort_order = (query_params.sort_order or "asc").lower()
        search = query_params.search

        page_size = max(1, min(page_size, 100))
        page_index = max(1, page_index)
        if sort_by not in UserService.ALLOWED_SORT_FIELDS:
            sort_by = "email"
        if sort_order not in {"asc", "desc"}:
            sort_order = "asc"

        statement = select(Users)
        if search:
            search = search.replace("%", "\\%").replace("_", "\\_")
            filters = [Users.email.ilike(f"%{search}%")]
            statement = statement.where(or_(*filters))

        count_statement = select(func.count()).select_from(statement.subquery())
        count = session.exec(count_statement).one()

        sort_column = getattr(Users, sort_by, Users.email)
        order_by_clause = asc(sort_column) if sort_order.lower() == "asc" else desc(sort_column)

        users = session.exec(
            statement.order_by(order_by_clause).offset((page_index - 1) * page_size).limit(page_size)
        ).all()
        return {"data": users, "count": count}

    @staticmethod
    def get_by_id(*, session: Session, user_id: uuid.UUID):
        user = session.get(Users, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    @staticmethod
    def create_user(*, session: Session, user_in: Any):
        payload = UserService._dump_payload(user_in)
        email = payload.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")

        existing_email = session.exec(select(Users).where(Users.email == email)).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")

        password = payload.get("password")
        if not password:
            raise HTTPException(status_code=400, detail="Password is required")

        new_user = Users(
            email=email,
            hashed_password=get_password_hash(password),
            is_active=payload.get("is_active", True),
            is_superuser=payload.get("is_superuser", False),
        )
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return new_user

    @staticmethod
    def update_user(*, session: Session, user_id: uuid.UUID, user_in: Any):
        user = session.get(Users, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        update_data = UserService._dump_payload(user_in)
        if "email" in update_data and update_data["email"] != user.email:
            existing_email = session.exec(
                select(Users).where(
                    Users.email == update_data["email"],
                    Users.id != user_id,
                )
            ).first()
            if existing_email:
                raise HTTPException(status_code=400, detail="Email already exists")

        if "password" in update_data:
            password = update_data.pop("password")
            if password:
                update_data["hashed_password"] = get_password_hash(password)

        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)

        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    @staticmethod
    def delete_user(*, session: Session, user_id: uuid.UUID) -> dict:
        user = session.get(Users, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if hasattr(user, "is_deleted"):
            user.is_deleted = True
            session.add(user)
        else:
            session.delete(user)
        session.commit()
        return {"id": user_id, "message": "User deleted successfully"}
