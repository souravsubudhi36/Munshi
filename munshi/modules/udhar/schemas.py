"""Pydantic schemas for udhar (credit) module."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class ItemDetail(BaseModel):
    name: str
    qty: float
    price: float


class CreditInput(BaseModel):
    customer_name: str
    amount: float = Field(gt=0)
    description: str | None = None
    items: list[ItemDetail] | None = None
    transaction_date: date | None = None


class PaymentInput(BaseModel):
    customer_name: str
    amount: float = Field(gt=0)
    description: str | None = None
    transaction_date: date | None = None


class NewCustomerInput(BaseModel):
    name: str
    phone: str | None = None
    aliases: list[str] = []
    address: str | None = None


class CustomerOut(BaseModel):
    id: int
    name: str
    phone: str | None
    aliases: list[str]
    outstanding_amount: float = 0.0

    model_config = {"from_attributes": True}


class UdharTransactionOut(BaseModel):
    id: int
    customer_id: int
    transaction_type: str
    amount: float
    description: str | None
    transaction_date: date
    recorded_at: datetime

    model_config = {"from_attributes": True}


class OutstandingResult(BaseModel):
    customer_id: int
    customer_name: str
    phone: str | None
    outstanding_amount: float
    transactions: list[UdharTransactionOut] = []
