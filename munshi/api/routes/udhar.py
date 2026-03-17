"""Udhar (credit) API routes."""

from fastapi import APIRouter, HTTPException

from munshi.db.database import get_session
from munshi.modules.udhar.schemas import (
    CreditInput,
    CustomerOut,
    NewCustomerInput,
    OutstandingResult,
    PaymentInput,
    UdharTransactionOut,
)
from munshi.modules.udhar.service import AmbiguousCustomerError, UdharService

router = APIRouter(prefix="/udhar", tags=["udhar"])

SHOP_ID = 1


@router.get("/outstanding", response_model=list[OutstandingResult])
async def get_all_outstanding():
    async with get_session() as db:
        svc = UdharService(db, SHOP_ID)
        return await svc.get_outstanding()


@router.get("/outstanding/{customer_name}", response_model=list[OutstandingResult])
async def get_customer_outstanding(customer_name: str):
    async with get_session() as db:
        svc = UdharService(db, SHOP_ID)
        try:
            return await svc.get_outstanding(customer_name)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))


@router.post("/credit", status_code=201)
async def add_credit(data: CreditInput):
    async with get_session() as db:
        svc = UdharService(db, SHOP_ID)
        try:
            txn, customer = await svc.add_credit(data)
            return {"transaction": txn, "customer": customer}
        except AmbiguousCustomerError as e:
            raise HTTPException(status_code=422, detail={"message": str(e), "candidates": e.candidates})
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))


@router.post("/payment", status_code=201)
async def record_payment(data: PaymentInput):
    async with get_session() as db:
        svc = UdharService(db, SHOP_ID)
        try:
            txn, customer = await svc.record_payment(data)
            return {"transaction": txn, "customer": customer}
        except AmbiguousCustomerError as e:
            raise HTTPException(status_code=422, detail={"message": str(e), "candidates": e.candidates})
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))


@router.post("/customers", response_model=CustomerOut, status_code=201)
async def create_customer(data: NewCustomerInput):
    async with get_session() as db:
        svc = UdharService(db, SHOP_ID)
        return await svc.create_customer(data)
