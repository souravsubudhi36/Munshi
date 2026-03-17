"""Pydantic schemas for inventory module."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class ProductInput(BaseModel):
    name: str
    name_hindi: str | None = None
    aliases: list[str] = []
    barcode: str | None = None
    category: str | None = None
    unit: Literal["piece", "kg", "g", "l", "ml", "dozen", "pack"] = "piece"
    purchase_price: float | None = None
    selling_price: float | None = None
    initial_stock: float = 0.0
    min_stock_alert: float = 5.0
    shelf_location: str | None = None
    location_notes: str | None = None


class ProductOut(BaseModel):
    id: int
    name: str
    name_hindi: str | None
    aliases: list[str]
    category: str | None
    unit: str
    selling_price: float | None
    stock_quantity: float
    shelf_location: str | None
    location_notes: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class StockUpdateInput(BaseModel):
    product_name: str
    quantity: float = Field(description="Positive = stock in, negative = stock out")
    movement_type: Literal["purchase", "sale", "adjustment", "wastage"] = "purchase"
    unit_price: float | None = None
    notes: str | None = None
    movement_date: date | None = None


class LocationResult(BaseModel):
    product_id: int
    product_name: str
    shelf_location: str | None
    location_notes: str | None
    stock_quantity: float
