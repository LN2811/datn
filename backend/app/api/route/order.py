import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.order import OrderService


router = APIRouter(prefix="/orders", tags=["Orders"])


class OrderCreateBody(BaseModel):
    plan_id: uuid.UUID
    payment_method: Optional[str] = "momo"


@router.post("/create")
def create_order(
    order_in: OrderCreateBody,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
) -> dict:
    return OrderService(session).create_order(
        user_id=current_user.id,
        plan_id=order_in.plan_id,
        order_code=f"ORD-{uuid.uuid4().hex[:12].upper()}",
        payment_method=order_in.payment_method or "momo",
    )


@router.get("")
def get_my_orders(
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
    status: str | None = None,
    payment_status: str | None = None,
    payment_method: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> dict:
    return OrderService(session).list_orders(
        user_id=current_user.id,
        status=status,
        payment_status=payment_status,
        payment_method=payment_method,
        skip=skip,
        limit=limit,
    )