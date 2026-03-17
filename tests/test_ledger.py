"""Tests for ledger service."""

import pytest
from datetime import date

from munshi.modules.ledger.schemas import ExpenseInput, SaleInput
from munshi.modules.ledger.service import LedgerService


@pytest.mark.asyncio
async def test_add_sale(db_session):
    svc = LedgerService(db_session, shop_id=1)
    entry = await svc.add_sale(SaleInput(amount=300.0, description="chai"))

    assert entry.id is not None
    assert entry.amount == 300.0
    assert entry.entry_type == "sale"
    assert entry.payment_mode == "cash"
    assert entry.description == "chai"


@pytest.mark.asyncio
async def test_add_expense(db_session):
    svc = LedgerService(db_session, shop_id=1)
    entry = await svc.add_expense(ExpenseInput(amount=150.0, description="bijli bill"))

    assert entry.entry_type == "expense"
    assert entry.amount == 150.0


@pytest.mark.asyncio
async def test_daily_summary_empty(db_session):
    svc = LedgerService(db_session, shop_id=1)
    summary = await svc.daily_summary(date.today())

    assert summary.total_sales == 0.0
    assert summary.total_expenses == 0.0
    assert summary.net_profit == 0.0
    assert summary.transaction_count == 0


@pytest.mark.asyncio
async def test_daily_summary_with_entries(db_session):
    svc = LedgerService(db_session, shop_id=1)
    await svc.add_sale(SaleInput(amount=1000.0, description="atta"))
    await svc.add_sale(SaleInput(amount=500.0, description="tel"))
    await svc.add_expense(ExpenseInput(amount=200.0, description="poly bags"))

    summary = await svc.daily_summary()
    assert summary.total_sales == 1500.0
    assert summary.total_expenses == 200.0
    assert summary.net_profit == 1300.0
    assert summary.transaction_count == 3


@pytest.mark.asyncio
async def test_sale_upi_payment(db_session):
    svc = LedgerService(db_session, shop_id=1)
    entry = await svc.add_sale(SaleInput(amount=50.0, payment_mode="upi"))
    assert entry.payment_mode == "upi"
