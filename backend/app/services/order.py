import uuid
from datetime import datetime
from typing import Any
from sqlmodel import Session, func, select
from app.models.schemas.Order.order_schemas import OrderCreate, OrderRead, OrderUpdate
from app.models.schemas.payment.payment_schemas import PaymentTransactionCreate, PaymentTransactionRead
from app.models.models import Order, PaymentTransaction

class OrderService:
    def __init__(self, session: Session):
        self.session = session

    def create_order(
        self,
        *,
        user_id: uuid.UUID,
        plan_id: uuid.UUID,
        order_code: str,
        plan_name: str,
        amount: int,
        currency: str = "VND",
        payment_method: str | None = "momo",
    ) -> dict:
        existing_pending_order = self.session.exec(
            select(Order).where(
                Order.user_id == user_id,
                Order.plan_id == plan_id,
                Order.status == "pending",
                Order.payment_status == "unpaid",
            )
        ).first()

        if existing_pending_order:
            return {
                "error": "User already has a pending order for this plan",
                "order": existing_pending_order,
            }

        order = Order(
            user_id=user_id,
            plan_id=plan_id,
            order_code=order_code,
            plan_name=plan_name,
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            status="pending",
            payment_status="unpaid",
        )

        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)

        return {"order": order}
    
    def get_order(
        self,
        *,
        user_id: uuid.UUID,
        status: str | None = None,
        payment_status: str | None = None,
        payment_method: str | None = None,
        skip: int = 0,
        limit: int = 20,
    )-> dict:
        conditions = []
        if user_id:
            conditions.append(Order.user_id == user_id)
        if status:
            conditions.append(Order.status == status)
        if payment_status:
            conditions.append(Order.payment_status == payment_status)
        if payment_method:
            conditions.append(Order.payment_method == payment_method)
        count_statement = select(func.count()).where(*conditions)
        total = self.session.exec(count_statement).scalar()
        statement = select(Order).where(*conditions).offset(skip).limit(limit)
        statement = (
            statement.order_by(Order.created_at.desc()).offset(skip).limit(limit)
        )
        orders = self.session.exec(statement).all()
        return {
            "items": orders,
            "total": total,
            "skip": skip,
            "limit": limit,
        }