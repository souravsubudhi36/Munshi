"""Inventory API routes."""

from fastapi import APIRouter, HTTPException

from munshi.db.database import get_session
from munshi.modules.inventory.schemas import (
    LocationResult,
    ProductInput,
    ProductOut,
    StockUpdateInput,
)
from munshi.modules.inventory.service import InventoryService

router = APIRouter(prefix="/inventory", tags=["inventory"])

SHOP_ID = 1


@router.post("/products", response_model=ProductOut, status_code=201)
async def add_product(data: ProductInput):
    async with get_session() as db:
        svc = InventoryService(db, SHOP_ID)
        return await svc.add_product(data)


@router.get("/products/low-stock", response_model=list[ProductOut])
async def get_low_stock():
    async with get_session() as db:
        svc = InventoryService(db, SHOP_ID)
        return await svc.get_low_stock_alerts()


@router.get("/location/{product_name}", response_model=LocationResult)
async def find_location(product_name: str):
    async with get_session() as db:
        svc = InventoryService(db, SHOP_ID)
        try:
            return await svc.find_location(product_name)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))


@router.get("/stock/{product_name}", response_model=LocationResult)
async def check_stock(product_name: str):
    async with get_session() as db:
        svc = InventoryService(db, SHOP_ID)
        try:
            return await svc.check_stock(product_name)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))


@router.post("/stock/movement", response_model=ProductOut)
async def update_stock(data: StockUpdateInput):
    async with get_session() as db:
        svc = InventoryService(db, SHOP_ID)
        try:
            return await svc.update_stock(data)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
