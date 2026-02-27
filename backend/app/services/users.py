import uuid
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session, asc, desc, func, or_, select

from app.models.models import Users


class UserService:
    @staticmethod
    def _dump_payload(schema_obj: Any) -> dict:
        if hasattr(schema_obj, "model_dump"):
            return schema_obj.model_dump(exclude_unset=True)
        if hasattr(schema_obj, "dict"):
            return schema_obj.dict(exclude_unset=True)
        return {}

    def get_user(
        self,
        *,
        session: Session,
        page_size: int = 20,
        page_index: int = 1,
        sort_by: str = "email",
        sort_order: str = "asc",
        search: str | None = None,
    ) -> dict:
        page_size = max(1, min(page_size, 100))
        page_index = max(1, page_index)

        statement = select(Users)
        if search:
            search = search.replace("%", "\\%").replace("_", "\\_")
            filters = [Users.email.ilike(f"%{search}%")]
            if hasattr(Users, "name"):
                filters.append(getattr(Users, "name").ilike(f"%{search}%"))
            statement = statement.where(or_(*filters))

        count_statement = select(func.count()).select_from(statement.subquery())
        count = session.exec(count_statement).one()

        sort_column = getattr(Users, sort_by, Users.email)
        order_by_clause = asc(sort_column) if sort_order.lower() == "asc" else desc(sort_column)

        users = session.exec(
            statement.order_by(order_by_clause).offset((page_index - 1) * page_size).limit(page_size)
        ).all()
        return {"data": users, "count": count}

    def get_by_id(self, *, session: Session, user_id: uuid.UUID):
        user = session.get(Users, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    def create_user(self, *, session: Session, user_in: Any):
        payload = self._dump_payload(user_in)
        email = payload.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")

        existing_email = session.exec(select(Users).where(Users.email == email)).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")

        hashed_password = payload.get("hashed_password") or payload.get("password")
        if not hashed_password:
            raise HTTPException(status_code=400, detail="Password is required")

        new_user = Users(
            email=email,
            hashed_password=hashed_password,
            is_active=payload.get("is_active", True),
            is_superuser=payload.get("is_superuser", payload.get("is_admin", False)),
        )
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return new_user

    def update_user(self, *, session: Session, user_id: uuid.UUID, user_in: Any):
        user = session.get(Users, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        update_data = self._dump_payload(user_in)
        if "email" in update_data and update_data["email"] != user.email:
            existing_email = session.exec(
                select(Users).where(
                    Users.email == update_data["email"],
                    Users.id != user_id,
                )
            ).first()
            if existing_email:
                raise HTTPException(status_code=400, detail="Email already exists")

        if "password" in update_data and "hashed_password" not in update_data:
            update_data["hashed_password"] = update_data.pop("password")

        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)

        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    def delete_user(self, *, session: Session, user_id: uuid.UUID) -> dict:
        user = session.get(Users, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if hasattr(user, "is_deleted"):
            user.is_deleted = True
            session.add(user)
        else:
            session.delete(user)
        session.commit()
        return {"id": str(user_id), "message": "User deleted successfully"}
