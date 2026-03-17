"""Ledger API routes."""

from datetime import date

from fastapi import APIRouter, HTTPException

from munshi.db.database import get_session
from munshi.modules.ledger.schemas import DailySummary, ExpenseInput, LedgerEntryOut, SaleInput
from munshi.modules.ledger.service import LedgerService

router = APIRouter(prefix="/ledger", tags=["ledger"])

SHOP_ID = 1  # Single-shop default


@router.post("/sale", response_model=LedgerEntryOut, status_code=201)
async def add_sale(data: SaleInput):
    async with get_session() as db:
        svc = LedgerService(db, SHOP_ID)
        return await svc.add_sale(data)


@router.post("/expense", response_model=LedgerEntryOut, status_code=201)
async def add_expense(data: ExpenseInput):
    async with get_session() as db:
        svc = LedgerService(db, SHOP_ID)
        return await svc.add_expense(data)


@router.get("/summary", response_model=DailySummary)
async def daily_summary(date: date | None = None):
    async with get_session() as db:
        svc = LedgerService(db, SHOP_ID)
        return await svc.daily_summary(date)
