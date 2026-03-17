"""Repository for ledger entries."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from munshi.db.models import LedgerEntry


class LedgerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, entry: LedgerEntry) -> LedgerEntry:
        self.session.add(entry)
        await self.session.flush()
        await self.session.refresh(entry)
        return entry

    async def get_by_date(self, shop_id: int, entry_date: date) -> list[LedgerEntry]:
        result = await self.session.execute(
            select(LedgerEntry)
            .where(LedgerEntry.shop_id == shop_id, LedgerEntry.entry_date == entry_date)
            .order_by(LedgerEntry.recorded_at)
        )
        return list(result.scalars().all())

    async def get_by_date_range(
        self, shop_id: int, from_date: date, to_date: date
    ) -> list[LedgerEntry]:
        result = await self.session.execute(
            select(LedgerEntry)
            .where(
                LedgerEntry.shop_id == shop_id,
                LedgerEntry.entry_date >= from_date,
                LedgerEntry.entry_date <= to_date,
            )
            .order_by(LedgerEntry.entry_date, LedgerEntry.recorded_at)
        )
        return list(result.scalars().all())

    async def daily_totals(self, shop_id: int, entry_date: date) -> dict:
        result = await self.session.execute(
            select(
                LedgerEntry.entry_type,
                func.sum(LedgerEntry.amount).label("total"),
                func.count(LedgerEntry.id).label("count"),
            )
            .where(LedgerEntry.shop_id == shop_id, LedgerEntry.entry_date == entry_date)
            .group_by(LedgerEntry.entry_type)
        )
        rows = result.all()
        totals = {"sale": 0.0, "expense": 0.0, "adjustment": 0.0, "count": 0}
        for entry_type, total, count in rows:
            totals[entry_type] = float(total or 0)
            totals["count"] += count
        totals["net"] = totals["sale"] - totals["expense"]
        return totals

    async def get_unsynced(self, shop_id: int, limit: int = 100) -> list[LedgerEntry]:
        result = await self.session.execute(
            select(LedgerEntry)
            .where(LedgerEntry.shop_id == shop_id, LedgerEntry.synced == False)  # noqa: E712
            .limit(limit)
        )
        return list(result.scalars().all())
