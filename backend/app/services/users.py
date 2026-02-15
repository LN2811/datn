import uuid
from datetime import datetime
from fastapi import HTTPException, Request
from sqlmodel import Session, asc, desc, func, or_, select
from app.models.schemas.users.user_schemas import UserCreate, UserUpdate, DeleteUser

class UserService:
    def __init__(self):
        self.author = Author()
    
    def get_user(self, session: Session, query_params: QueryParams, request: Request
    )-> UserPublic:
        page_size = query_params.page_size
        page_index = query_params.page_index
        sort_by = query_params.sort_by
        sort_order = query_params.sort_order
        search = query_params.search

        statement = (
            select(Users)
            .where(Users.is_deleted.is_(False))
        )

        if search:
            search = search.replace("%", "\\%").replace("_", "\\_")
            filter_clause = or_(
                Users.name.ilike(f"%{search}%"),
                Users.email.ilike(f"%{search}%")
            )
            statement = statement.where(filter_clause)
        
        count_statement = select(func.count()).select_from(statement.subquery())
        count = session.exec(count_statement).scalar_one()

        max page_index = (count - 1) // page_size + 1 if count > 0 else 1
        if page_index > max_page_index:
            page_index = max_page_index

        order_by_clause = asc(getattr(Users, sort_by)) if sort_order == "asc" else desc(getattr(Users, sort_by))

        if sort_by and sort_order:
            sort_column = getattr(Users, sort_by, None)
            if sort_column:
                order_by_column = [asc(sort_column) if sort_order == "asc" else desc(sort_column)]

        statement = statement.order_by(*order_by_clause)
        statement = statement.offset((page_index - 1) * page_size).limit(page_size)
        users = session.exec(statement).all()
        return UsersPublic(data=users, count = count)

    def get_by_id(self, *, session: Session, user_id: uuid.UUID, request: Request) 
    -> UsersPublic:
        user = session.get(Users, user_id)
        if not user or user.is_deleted:
            raise HTTPException(status_code=404, detail="User not found")
        return UsersPublic.from_orm(user)
    
    def create_user(self, *, session: Session, user_in: UserCreate, request: Request) -> UsersPublic:
        authorized = self.author.is_authorized(request = request)
        existing_email = session.exec(
            select(Users).where(Users.email == user_in.email, Users.is_deleted.is_(False))
        ).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")
        user_data = user_in.dict()
        user_data["hashed_password"] = pwd_context.hash(user_in.password)
        user_data["created_by_id"] = authorized.get("id")
        
        new_user = Users(**user_data)
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return UsersPublic.model_validate(new_user)

    def update_user(self, *, session: Session, user_id: uuid.UUID, user_in: UserUpdate, request: Request) -> UsersPublic:
        user = session.get(Users, user_id)
        authorized = self.author.is_authorized(request = request)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if authorized["role"] != "admin" and authorized["id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this user")
        update_data = user_in.dict(exclude_unset=True)

        if "email" in update_data:
            existing_email = session.exec(
                select(Users).where(Users.email == update_data["email"], Users.id != user_id, Users.is_deleted.is_(False))
            ).first()
            if existing_email:
                raise HTTPException(status_code=400, detail="Email already exists")

        if "password" in update_data:
            update_data["hashed_password"] = pwd_context.hash(update_data.pop("password"))
            del update_data["password"]

        for field, value in update_data.items():
            setattr(user, field, value)

        session.add(user)
        session.commit()
        session.refresh(user)
        return UsersPublic.model_validate(user)


    def delete_user(self, *, session: Session, user_id: uuid.UUID, request: Request) -> DeleteUser:
        user = session.get(Users, user_id)
        authorized = self.author.is_authorized(request = request)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if authorized["role"] != "admin" and authorized["id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this user")
        user.is_deleted = True
        session.add(user)
        session.commit()
        return DeleteUser(id=user_id, message="User deleted successfully")


        