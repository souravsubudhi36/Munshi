"""Ledger service — daily sales and expense tracking."""

import pendulum
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from munshi.db.models import LedgerEntry
from munshi.db.repositories.ledger_repo import LedgerRepository
from munshi.modules.ledger.schemas import DailySummary, ExpenseInput, LedgerEntryOut, SaleInput


def _today() -> "pendulum.Date":
    return pendulum.today("Asia/Kolkata").date()


class LedgerService:
    def __init__(self, session: AsyncSession, shop_id: int) -> None:
        self.repo = LedgerRepository(session)
        self.shop_id = shop_id

    async def add_sale(self, data: SaleInput) -> LedgerEntryOut:
        entry_date = data.entry_date or _today()
        entry = LedgerEntry(
            shop_id=self.shop_id,
            entry_type="sale",
            amount=data.amount,
            description=data.description,
            category=data.category,
            payment_mode=data.payment_mode,
            entry_date=entry_date,
        )
        saved = await self.repo.add(entry)
        logger.info(f"Sale recorded: ₹{data.amount} [{data.description}]")
        return LedgerEntryOut.model_validate(saved)

    async def add_expense(self, data: ExpenseInput) -> LedgerEntryOut:
        entry_date = data.entry_date or _today()
        entry = LedgerEntry(
            shop_id=self.shop_id,
            entry_type="expense",
            amount=data.amount,
            description=data.description,
            category=data.category,
            payment_mode="cash",
            entry_date=entry_date,
        )
        saved = await self.repo.add(entry)
        logger.info(f"Expense recorded: ₹{data.amount} [{data.description}]")
        return LedgerEntryOut.model_validate(saved)

    async def daily_summary(self, target_date=None) -> DailySummary:
        d = target_date or _today()
        totals = await self.repo.daily_totals(self.shop_id, d)
        entries_raw = await self.repo.get_by_date(self.shop_id, d)
        entries = [LedgerEntryOut.model_validate(e) for e in entries_raw]
        return DailySummary(
            date=d,
            total_sales=totals["sale"],
            total_expenses=totals["expense"],
            net_profit=totals["net"],
            transaction_count=totals["count"],
            entries=entries,
        )
