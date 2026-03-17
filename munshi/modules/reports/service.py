"""Reports service — weekly/monthly P&L summaries and udhar aging."""

from datetime import date, timedelta

import pendulum
from sqlalchemy.ext.asyncio import AsyncSession

from munshi.db.repositories.ledger_repo import LedgerRepository
from munshi.db.repositories.udhar_repo import CustomerRepository, UdharRepository


class ReportsService:
    def __init__(self, session: AsyncSession, shop_id: int) -> None:
        self.session = session
        self.shop_id = shop_id
        self.ledger_repo = LedgerRepository(session)
        self.udhar_repo = UdharRepository(session)

    async def weekly_summary(self, reference_date: date | None = None) -> dict:
        today = reference_date or pendulum.today("Asia/Kolkata").date()
        # Week starts Monday
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)

        entries = await self.ledger_repo.get_by_date_range(self.shop_id, start, end)

        daily: dict[date, dict] = {}
        for entry in entries:
            d = entry.entry_date
            if d not in daily:
                daily[d] = {"sales": 0.0, "expenses": 0.0}
            if entry.entry_type == "sale":
                daily[d]["sales"] += entry.amount
            elif entry.entry_type == "expense":
                daily[d]["expenses"] += entry.amount

        total_sales = sum(v["sales"] for v in daily.values())
        total_expenses = sum(v["expenses"] for v in daily.values())

        return {
            "period": f"{start} to {end}",
            "total_sales": total_sales,
            "total_expenses": total_expenses,
            "net_profit": total_sales - total_expenses,
            "daily_breakdown": {str(k): v for k, v in sorted(daily.items())},
        }

    async def udhar_aging(self, days_threshold: int = 30) -> dict:
        """Returns customers with udhar older than threshold days."""
        all_outstanding = await self.udhar_repo.outstanding_per_customer(self.shop_id)
        today = pendulum.today("Asia/Kolkata").date()

        overdue = []
        for row in all_outstanding:
            if row["outstanding"] <= 0:
                continue
            txns = await self.udhar_repo.get_by_customer(row["customer_id"])
            # Find the oldest unpaid credit
            credits = [t for t in txns if t.transaction_type == "credit"]
            if credits:
                oldest = min(t.transaction_date for t in credits)
                days_old = (today - oldest).days
                if days_old >= days_threshold:
                    overdue.append({
                        **row,
                        "days_since_oldest_credit": days_old,
                        "oldest_credit_date": str(oldest),
                    })

        return {
            "threshold_days": days_threshold,
            "overdue_count": len(overdue),
            "total_overdue_amount": sum(r["outstanding"] for r in overdue),
            "customers": overdue,
        }
