from datetime import datetime

from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.models.models import PricingPlans, UserSubscriptions, Users


class AdminStatsService:
    MONTH_LABELS = [
        "Tháng 1",
        "Tháng 2",
        "Tháng 3",
        "Tháng 4",
        "Tháng 5",
        "Tháng 6",
        "Tháng 7",
        "Tháng 8",
        "Tháng 9",
        "Tháng 10",
        "Tháng 11",
        "Tháng 12",
    ]

    QUARTER_LABELS = ["Quý 1", "Quý 2", "Quý 3", "Quý 4"]

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _safe_year(year: int | None) -> int:
        current_year = datetime.utcnow().year
        if year is None:
            return current_year
        return max(2000, min(int(year), current_year + 1))

    def _count_users(self) -> dict:
        total_users = self.session.exec(select(func.count(Users.id))).one()
        active_users = self.session.exec(
            select(func.count(Users.id)).where(Users.is_active == True)
        ).one()
        admin_users = self.session.exec(
            select(func.count(Users.id)).where(Users.is_superuser == True)
        ).one()
        return {
            "total_users": total_users or 0,
            "active_users": active_users or 0,
            "admin_users": admin_users or 0,
        }

    def _user_registrations_by_month(self, *, year: int) -> list[dict]:
        rows = self.session.exec(
            select(
                func.extract("month", Users.created_at).label("month"),
                func.count(Users.id).label("total"),
            )
            .where(func.extract("year", Users.created_at) == year)
            .group_by(func.extract("month", Users.created_at))
            .order_by(func.extract("month", Users.created_at))
        ).all()
        totals = {int(month): int(total) for month, total in rows}
        return [
            {
                "month": month,
                "label": self.MONTH_LABELS[month - 1],
                "count": totals.get(month, 0),
            }
            for month in range(1, 13)
        ]

    def _subscription_updates_by_quarter(self, *, year: int) -> list[dict]:
        rows = self.session.exec(
            select(
                func.extract("quarter", UserSubscriptions.start_date).label("quarter"),
                func.count(UserSubscriptions.id).label("total"),
            )
            .where(func.extract("year", UserSubscriptions.start_date) == year)
            .group_by(func.extract("quarter", UserSubscriptions.start_date))
            .order_by(func.extract("quarter", UserSubscriptions.start_date))
        ).all()
        totals = {int(quarter): int(total) for quarter, total in rows}
        return [
            {
                "quarter": quarter,
                "label": self.QUARTER_LABELS[quarter - 1],
                "count": totals.get(quarter, 0),
            }
            for quarter in range(1, 5)
        ]

    def _subscription_updates_by_plan(self, *, year: int) -> list[dict]:
        rows = self.session.exec(
            select(
                PricingPlans.id,
                PricingPlans.name,
                func.count(UserSubscriptions.id).label("total"),
            )
            .join(PricingPlans, UserSubscriptions.plan_id == PricingPlans.id)
            .where(func.extract("year", UserSubscriptions.start_date) == year)
            .group_by(PricingPlans.id, PricingPlans.name)
            .order_by(func.count(UserSubscriptions.id).desc(), PricingPlans.name)
        ).all()
        return [
            {
                "plan_id": str(plan_id),
                "plan_name": plan_name,
                "count": int(total or 0),
            }
            for plan_id, plan_name, total in rows
        ]

    def _active_subscriptions_by_plan(self) -> list[dict]:
        now = datetime.utcnow()
        rows = self.session.exec(
            select(
                PricingPlans.id,
                PricingPlans.name,
                func.count(UserSubscriptions.id).label("total"),
            )
            .join(PricingPlans, UserSubscriptions.plan_id == PricingPlans.id)
            .where(or_(UserSubscriptions.end_date == None, UserSubscriptions.end_date > now))
            .group_by(PricingPlans.id, PricingPlans.name)
            .order_by(func.count(UserSubscriptions.id).desc(), PricingPlans.name)
        ).all()
        return [
            {
                "plan_id": str(plan_id),
                "plan_name": plan_name,
                "count": int(total or 0),
            }
            for plan_id, plan_name, total in rows
        ]

    def dashboard(self, *, year: int | None = None) -> dict:
        safe_year = self._safe_year(year)
        user_counts = self._count_users()
        registrations = self._user_registrations_by_month(year=safe_year)
        subscription_updates = self._subscription_updates_by_quarter(year=safe_year)
        total_subscription_updates = sum(item["count"] for item in subscription_updates)

        return {
            "year": safe_year,
            "totals": {
                **user_counts,
                "subscription_updates": total_subscription_updates,
            },
            "user_registrations_by_month": registrations,
            "subscription_updates_by_quarter": subscription_updates,
            "subscription_updates_by_plan": self._subscription_updates_by_plan(year=safe_year),
            "active_subscriptions_by_plan": self._active_subscriptions_by_plan(),
        }
