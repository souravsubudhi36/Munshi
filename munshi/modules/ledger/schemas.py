"""Pydantic schemas for ledger module."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class SaleInput(BaseModel):
    amount: float = Field(gt=0, description="Sale amount in rupees")
    description: str | None = None
    category: str | None = None
    payment_mode: Literal["cash", "upi", "card", "credit"] = "cash"
    entry_date: date | None = None  # defaults to today


class ExpenseInput(BaseModel):
    amount: float = Field(gt=0, description="Expense amount in rupees")
    description: str | None = None
    category: str | None = None
    entry_date: date | None = None


class LedgerEntryOut(BaseModel):
    id: int
    entry_type: str
    amount: float
    description: str | None
    category: str | None
    payment_mode: str
    entry_date: date
    recorded_at: datetime

    model_config = {"from_attributes": True}


class DailySummary(BaseModel):
    date: date
    total_sales: float
    total_expenses: float
    net_profit: float
    transaction_count: int
    entries: list[LedgerEntryOut] = []
