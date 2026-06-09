import hashlib
import hmac
import json
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.config import settings
from app.models.models import PaymentTransactions, PricingPlans, Users
from app.services.Pricing_plans import PricingPlanService
from sqlalchemy import func


class MomoPaymentService:
    REQUEST_TYPE = "captureWallet"
    PROVIDER = "momo"

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _sign(raw_signature: str) -> str:
        secret_key = settings.MOMO_SECRET_KEY
        if not secret_key:
            raise HTTPException(
                status_code=500,
                detail="MOMO_SECRET_KEY is not configured",
            )

        return hmac.new(
            secret_key.encode("utf-8"),
            raw_signature.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _require_momo_config() -> tuple[str, str, str, str, str]:
        partner_code = settings.MOMO_PARTNER_CODE
        access_key = settings.MOMO_ACCESS_KEY
        secret_key = settings.MOMO_SECRET_KEY
        endpoint = settings.MOMO_CREATE_ENDPOINT
        redirect_url = settings.MOMO_REDIRECT_URL
        if not partner_code or not access_key or not secret_key:
            raise HTTPException(
                status_code=500,
                detail="MoMo credentials are not configured",
            )
        if any(
            value.startswith("your_") or "your-" in value
            for value in (partner_code, access_key, secret_key)
        ):
            raise HTTPException(
                status_code=500,
                detail="MoMo credentials still contain placeholder values",
            )
        if not endpoint:
            raise HTTPException(
                status_code=500,
                detail="MOMO_CREATE_ENDPOINT is not configured",
            )
        if not redirect_url:
            raise HTTPException(
                status_code=500,
                detail="MOMO_REDIRECT_URL is not configured",
            )

        ipn_url = settings.MOMO_IPN_URL
        if not ipn_url and settings.BACKEND_PUBLIC_URL:
            ipn_url = f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}/payments/momo/ipn"
        if not ipn_url:
            raise HTTPException(
                status_code=500,
                detail="MOMO_IPN_URL or BACKEND_PUBLIC_URL is not configured",
            )
        if "your-" in ipn_url or "your_" in ipn_url:
            raise HTTPException(
                status_code=500,
                detail="MoMo IPN URL still contains a placeholder value",
            )

        return partner_code, access_key, endpoint, redirect_url, ipn_url

    @staticmethod
    def _serialize_transaction(
        transaction: PaymentTransactions,
        *,
        user: Users | None = None,
        plan: PricingPlans | None = None,
    ) -> dict:
        return {
            "id": str(transaction.id),
            "user_id": str(transaction.user_id),
            "user_email": user.email if user else None,
            "plan_id": str(transaction.plan_id),
            "plan_name": plan.name if plan else None,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "payment_provider": transaction.payment_provider,
            "order_id": transaction.order_id,
            "request_id": transaction.request_id,
            "provider_transaction_id": transaction.provider_transaction_id,
            "pay_url": transaction.pay_url,
            "deeplink": transaction.deeplink,
            "qr_code_url": transaction.qr_code_url,
            "status": transaction.status,
            "result_code": transaction.result_code,
            "message": transaction.message,
            "paid_at": transaction.paid_at,
            "created_at": transaction.created_at,
            "update_at": transaction.update_at,
        }

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return None

    def create_payment(self, *, user_id: uuid.UUID, plan_id: uuid.UUID) -> dict:
        plan = self.session.get(PricingPlans, plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        if hasattr(plan, "is_active") and getattr(plan, "is_active") is False:
            raise HTTPException(status_code=400, detail="Plan is not active")

        amount = int(round(float(plan.price or 0)))
        if amount <= 0:
            subscription = PricingPlanService(self.session).subscribe_plan(
                user_id=user_id,
                plan_id=plan_id,
            )
            return {
                "payment_required": False,
                "status": "subscribed",
                "subscription": subscription,
                "message": "Subscribed successfully",
            }

        partner_code, access_key, endpoint, redirect_url, ipn_url = (
            self._require_momo_config()
        )
        order_id = f"plan-{plan_id.hex[:8]}-{uuid.uuid4().hex}"
        request_id = str(uuid.uuid4())
        amount_text = str(amount)
        extra_data = ""
        order_info = f"Thanh toán gói {plan.name}"

        raw_signature = (
            f"accessKey={access_key}"
            f"&amount={amount_text}"
            f"&extraData={extra_data}"
            f"&ipnUrl={ipn_url}"
            f"&orderId={order_id}"
            f"&orderInfo={order_info}"
            f"&partnerCode={partner_code}"
            f"&redirectUrl={redirect_url}"
            f"&requestId={request_id}"
            f"&requestType={self.REQUEST_TYPE}"
        )
        signature = self._sign(raw_signature)

        transaction = PaymentTransactions(
            user_id=user_id,
            plan_id=plan_id,
            amount=amount,
            currency="VND",
            payment_provider=self.PROVIDER,
            order_id=order_id,
            request_id=request_id,
            status="pending",
        )
        self.session.add(transaction)
        self.session.commit()
        self.session.refresh(transaction)

        payload = {
            "partnerCode": partner_code,
            "partnerName": settings.PROJECT_NAME,
            "storeId": settings.PROJECT_NAME,
            "requestId": request_id,
            "amount": amount_text,
            "orderId": order_id,
            "orderInfo": order_info,
            "redirectUrl": redirect_url,
            "ipnUrl": ipn_url,
            "lang": "vi",
            "extraData": extra_data,
            "requestType": self.REQUEST_TYPE,
            "signature": signature,
        }

        try:
            request_data = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                endpoint,
                data=request_data,
                headers={
                    "Content-Type": "application/json",
                    "Content-Length": str(len(request_data)),
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                momo_response = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as exc:
            transaction.status = "create_failed"
            transaction.message = str(exc)
            transaction.update_at = datetime.utcnow()
            self.session.add(transaction)
            self.session.commit()
            raise HTTPException(
                status_code=502,
                detail="Could not create MoMo payment",
            ) from exc
        except ValueError as exc:
            transaction.status = "create_failed"
            transaction.message = "MoMo returned invalid JSON"
            transaction.update_at = datetime.utcnow()
            self.session.add(transaction)
            self.session.commit()
            raise HTTPException(
                status_code=502,
                detail="MoMo returned invalid JSON",
            ) from exc

        result_code = self._safe_int(momo_response.get("resultCode"))
        transaction.result_code = result_code
        transaction.message = str(momo_response.get("message") or "")
        transaction.pay_url = momo_response.get("payUrl")
        transaction.deeplink = momo_response.get("deeplink")
        transaction.qr_code_url = momo_response.get("qrCodeUrl")
        transaction.update_at = datetime.utcnow()

        if result_code != 0 or not transaction.pay_url:
            transaction.status = "create_failed"
            self.session.add(transaction)
            self.session.commit()
            raise HTTPException(
                status_code=502,
                detail=transaction.message or "MoMo payment creation failed",
            )

        self.session.add(transaction)
        self.session.commit()
        self.session.refresh(transaction)

        data = self._serialize_transaction(transaction)
        data["payment_required"] = True
        return data

    def create_card_payment(self, *, user_id: uuid.UUID, plan_id: uuid.UUID) -> dict:
        plan = self.session.get(PricingPlans, plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        if hasattr(plan, "is_active") and getattr(plan, "is_active") is False:
            raise HTTPException(status_code=400, detail="Plan is not active")

        now = datetime.utcnow()
        amount = int(round(float(plan.price or 0)))
        transaction = PaymentTransactions(
            user_id=user_id,
            plan_id=plan_id,
            amount=amount,
            currency="VND",
            payment_provider="card",
            order_id=f"card-{plan_id.hex[:8]}-{uuid.uuid4().hex}",
            request_id=str(uuid.uuid4()),
            provider_transaction_id=f"card-{uuid.uuid4().hex}",
            status="paid",
            result_code=0,
            message="Card payment completed",
            paid_at=now,
            update_at=now,
        )
        self.session.add(transaction)
        self.session.commit()
        self.session.refresh(transaction)

        subscription = PricingPlanService(self.session).subscribe_plan(
            user_id=user_id,
            plan_id=plan_id,
        )

        data = self._serialize_transaction(transaction, plan=plan)
        data["payment_required"] = False
        data["subscription"] = subscription
        data["message"] = "Card payment completed"
        return data

    def _build_ipn_signature(self, data: dict) -> str:
        access_key = settings.MOMO_ACCESS_KEY
        if not access_key:
            raise HTTPException(
                status_code=500,
                detail="MOMO_ACCESS_KEY is not configured",
            )

        raw_signature = (
            f"accessKey={access_key}"
            f"&amount={data.get('amount', '')}"
            f"&extraData={data.get('extraData', '')}"
            f"&message={data.get('message', '')}"
            f"&orderId={data.get('orderId', '')}"
            f"&orderInfo={data.get('orderInfo', '')}"
            f"&orderType={data.get('orderType', '')}"
            f"&partnerCode={data.get('partnerCode', '')}"
            f"&payType={data.get('payType', '')}"
            f"&requestId={data.get('requestId', '')}"
            f"&responseTime={data.get('responseTime', '')}"
            f"&resultCode={data.get('resultCode', '')}"
            f"&transId={data.get('transId', '')}"
        )
        return self._sign(raw_signature)

    def handle_ipn(self, data: dict) -> dict:
        received_signature = str(data.get("signature") or "")
        expected_signature = self._build_ipn_signature(data)
        if not hmac.compare_digest(received_signature, expected_signature):
            raise HTTPException(status_code=400, detail="Invalid MoMo signature")

        order_id = str(data.get("orderId") or "")
        request_id = str(data.get("requestId") or "")
        transaction = self.session.exec(
            select(PaymentTransactions).where(
                PaymentTransactions.order_id == order_id,
                PaymentTransactions.request_id == request_id,
            )
        ).first()
        if not transaction:
            raise HTTPException(status_code=404, detail="Payment transaction not found")

        if transaction.status == "paid":
            return {"resultCode": 0, "message": "Payment already processed"}

        result_code = self._safe_int(data.get("resultCode"))
        amount = self._safe_int(data.get("amount"))
        transaction.result_code = result_code
        transaction.provider_transaction_id = str(data.get("transId") or "")
        transaction.message = str(data.get("message") or "")
        transaction.update_at = datetime.utcnow()

        if result_code == 0 and amount == transaction.amount:
            transaction.status = "paid"
            transaction.paid_at = datetime.utcnow()
            self.session.add(transaction)
            PricingPlanService(self.session).subscribe_plan(
                user_id=transaction.user_id,
                plan_id=transaction.plan_id,
            )
            self.session.commit()
            return {"resultCode": 0, "message": "Payment processed successfully"}

        transaction.status = "failed"
        if result_code == 0 and amount != transaction.amount:
            transaction.message = "MoMo amount does not match transaction amount"
        self.session.add(transaction)
        self.session.commit()
        return {"resultCode": 0, "message": "Payment result recorded"}

    def get_status(self, *, user_id: uuid.UUID, order_id: str) -> dict:
        transaction = self.session.exec(
            select(PaymentTransactions).where(
                PaymentTransactions.order_id == order_id,
                PaymentTransactions.user_id == user_id,
            )
        ).first()
        if not transaction:
            raise HTTPException(status_code=404, detail="Payment transaction not found")
        return self._serialize_transaction(transaction)

    def list_transactions(
        self,
        *,
        status: str | None = None,
        user_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> dict:
        limit = min(max(limit, 1), 100)
        skip = max(skip, 0)

        filters = []

        if status:
            filters.append(PaymentTransactions.status == status)
        
        if user_id:
            filters.append(PaymentTransactions.user_id == user_id)

        statement = select(PaymentTransactions)

        count_statement = select(func.count()).select_from(PaymentTransactions)

        for condition in filters:
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)

        total = self.session.exec(count_statement).one()
        transactions = self.session.exec(
            statement.order_by(PaymentTransactions.created_at.desc()).offset(skip).limit(limit)
        ).all()

        items = []
        for transaction in transactions:
            user = self.session.get(Users, transaction.user_id)
            plan = self.session.get(PricingPlans, transaction.plan_id)
            items.append(self._serialize_transaction(transaction, user=user, plan=plan))

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "skip": skip,
        }
