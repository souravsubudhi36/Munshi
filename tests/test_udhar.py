"""Tests for udhar (credit) service."""

import pytest

from munshi.modules.udhar.schemas import CreditInput, NewCustomerInput, PaymentInput
from munshi.modules.udhar.service import AmbiguousCustomerError, UdharService


@pytest.mark.asyncio
async def test_create_customer(db_session):
    svc = UdharService(db_session, shop_id=1)
    customer = await svc.create_customer(
        NewCustomerInput(name="Ramesh Sharma", phone="9876543210", aliases=["Sharma ji"])
    )
    assert customer.id is not None
    assert customer.name == "Ramesh Sharma"
    assert "Sharma ji" in customer.aliases


@pytest.mark.asyncio
async def test_add_credit(db_session):
    svc = UdharService(db_session, shop_id=1)
    await svc.create_customer(NewCustomerInput(name="Suresh Kumar"))

    txn, customer = await svc.add_credit(
        CreditInput(customer_name="Suresh", amount=200.0, description="atta 5kg")
    )
    assert txn.transaction_type == "credit"
    assert txn.amount == 200.0
    assert customer.outstanding_amount == 200.0


@pytest.mark.asyncio
async def test_record_payment_reduces_outstanding(db_session):
    svc = UdharService(db_session, shop_id=1)
    await svc.create_customer(NewCustomerInput(name="Priya Devi"))

    await svc.add_credit(CreditInput(customer_name="Priya", amount=500.0))
    _, customer = await svc.record_payment(PaymentInput(customer_name="Priya", amount=300.0))
    assert customer.outstanding_amount == 200.0


@pytest.mark.asyncio
async def test_get_outstanding_all(db_session):
    svc = UdharService(db_session, shop_id=1)
    await svc.create_customer(NewCustomerInput(name="Anil Gupta"))
    await svc.create_customer(NewCustomerInput(name="Vijay Mehta"))
    await svc.add_credit(CreditInput(customer_name="Anil", amount=100.0))
    await svc.add_credit(CreditInput(customer_name="Vijay", amount=250.0))

    results = await svc.get_outstanding()
    assert len(results) == 2
    totals = {r.customer_name: r.outstanding_amount for r in results}
    assert totals["Anil Gupta"] == 100.0
    assert totals["Vijay Mehta"] == 250.0


@pytest.mark.asyncio
async def test_customer_not_found(db_session):
    svc = UdharService(db_session, shop_id=1)
    with pytest.raises(ValueError, match="No customer found"):
        await svc.add_credit(CreditInput(customer_name="Unknown Person", amount=100.0))


@pytest.mark.asyncio
async def test_fuzzy_name_matching(db_session):
    svc = UdharService(db_session, shop_id=1)
    await svc.create_customer(
        NewCustomerInput(name="Ramesh Yadav", aliases=["Ramesh bhai", "Ramesh ji"])
    )
    # Should match "Ramesh bhai" alias
    txn, customer = await svc.add_credit(
        CreditInput(customer_name="Ramesh bhai", amount=150.0)
    )
    assert customer.name == "Ramesh Yadav"
    assert txn.amount == 150.0
