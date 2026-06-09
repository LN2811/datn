import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.momo_payment import MomoPaymentService

router = APIRouter()


class MomoPaymentCreateBody(BaseModel):
    plan_id: uuid.UUID


class CardPaymentCreateBody(BaseModel):
    plan_id: uuid.UUID


@router.post("/momo/create")
def create_momo_payment(
    payment_in: MomoPaymentCreateBody,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
) -> dict:
    return MomoPaymentService(session).create_payment(
        user_id=current_user.id,
        plan_id=payment_in.plan_id,
    )


@router.post("/card/create")
def create_card_payment(
    payment_in: CardPaymentCreateBody,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
) -> dict:
    return MomoPaymentService(session).create_card_payment(
        user_id=current_user.id,
        plan_id=payment_in.plan_id,
    )


@router.post("/momo/ipn")
def momo_ipn(
    data: dict[str, Any],
    session: SessionDep,
) -> dict:
    return MomoPaymentService(session).handle_ipn(data)


@router.get("/momo/status/{order_id}")
def get_momo_payment_status(
    order_id: str,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
) -> dict:
    return MomoPaymentService(session).get_status(
        user_id=current_user.id,
        order_id=order_id,
    )


@router.get("/status/{order_id}")
def get_payment_status(
    order_id: str,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
) -> dict:
    return MomoPaymentService(session).get_status(
        user_id=current_user.id,
        order_id=order_id,
    )


@router.get("/admin/transactions")
def list_admin_transactions(
    session: SessionDep,
    status: str | None = None,
    user_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 20,
    _: Users = Depends(Authen.require_admin),
) -> dict:
    return MomoPaymentService(session).list_transactions(
        status=status,
        user_id=user_id,
        skip=skip,
        limit=limit,
    )


@router.get("/admin/payments/transactions", include_in_schema=False)
def list_admin_transactions_legacy(
    session: SessionDep,
    status: str | None = None,
    user_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 20,
    _: Users = Depends(Authen.require_admin),
) -> dict:
    return MomoPaymentService(session).list_transactions(
        status=status,
        user_id=user_id,
        skip=skip,
        limit=limit,
    )
