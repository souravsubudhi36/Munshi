"""Inventory service — product catalog, stock management, and location queries."""

import pendulum
from loguru import logger
from rapidfuzz import process as fuzz_process
from sqlalchemy.ext.asyncio import AsyncSession

from munshi.db.models import Product, StockMovement
from munshi.db.repositories.inventory_repo import ProductRepository, StockMovementRepository
from munshi.modules.inventory.schemas import (
    LocationResult,
    ProductInput,
    ProductOut,
    StockUpdateInput,
)

FUZZY_THRESHOLD = 60


def _today():
    return pendulum.today("Asia/Kolkata").date()


class InventoryService:
    def __init__(self, session: AsyncSession, shop_id: int) -> None:
        self.session = session
        self.product_repo = ProductRepository(session)
        self.movement_repo = StockMovementRepository(session)
        self.shop_id = shop_id

    async def _find_product(self, name: str) -> list[tuple[Product, float]]:
        """Fuzzy-match a product name. Returns (product, score) list."""
        products = await self.product_repo.get_all_active(self.shop_id)
        if not products:
            return []

        candidates: list[tuple[Product, str]] = []
        for p in products:
            for alias in p.all_names:
                candidates.append((p, alias))

        alias_strings = [alias for _, alias in candidates]
        matches = fuzz_process.extract(name, alias_strings, limit=5)

        seen_ids: set[int] = set()
        results: list[tuple[Product, float]] = []
        for _, score, idx in matches:
            if score < FUZZY_THRESHOLD:
                continue
            product = candidates[idx][0]
            if product.id not in seen_ids:
                seen_ids.add(product.id)
                results.append((product, score))

        return results

    async def add_product(self, data: ProductInput) -> ProductOut:
        product = Product(
            shop_id=self.shop_id,
            name=data.name,
            name_hindi=data.name_hindi,
            barcode=data.barcode,
            category=data.category,
            unit=data.unit,
            purchase_price=data.purchase_price,
            selling_price=data.selling_price,
            stock_quantity=data.initial_stock,
            min_stock_alert=data.min_stock_alert,
            shelf_location=data.shelf_location,
            location_notes=data.location_notes,
        )
        product.aliases = data.aliases
        saved = await self.product_repo.add(product)

        if data.initial_stock > 0:
            movement = StockMovement(
                shop_id=self.shop_id,
                product_id=saved.id,
                movement_type="purchase",
                quantity=data.initial_stock,
                unit_price=data.purchase_price,
                notes="Initial stock",
                movement_date=_today(),
            )
            await self.movement_repo.add(movement)

        logger.info(f"Product added: {data.name} (stock: {data.initial_stock})")
        return self._to_out(saved)

    async def find_location(self, product_name: str) -> LocationResult:
        """Answer 'where is X in the shop?'"""
        matches = await self._find_product(product_name)
        if not matches:
            raise ValueError(f"Product '{product_name}' not found in inventory.")

        product, _ = matches[0]
        return LocationResult(
            product_id=product.id,
            product_name=product.name,
            shelf_location=product.shelf_location,
            location_notes=product.location_notes,
            stock_quantity=product.stock_quantity,
        )

    async def check_stock(self, product_name: str) -> LocationResult:
        """Check current stock level for a product."""
        matches = await self._find_product(product_name)
        if not matches:
            raise ValueError(f"Product '{product_name}' not found.")

        product, _ = matches[0]
        return LocationResult(
            product_id=product.id,
            product_name=product.name,
            shelf_location=product.shelf_location,
            location_notes=product.location_notes,
            stock_quantity=product.stock_quantity,
        )

    async def update_stock(self, data: StockUpdateInput) -> ProductOut:
        """Record a stock movement and update the product's quantity."""
        matches = await self._find_product(data.product_name)
        if not matches:
            raise ValueError(f"Product '{data.product_name}' not found.")

        product, _ = matches[0]
        movement_date = data.movement_date or _today()

        movement = StockMovement(
            shop_id=self.shop_id,
            product_id=product.id,
            movement_type=data.movement_type,
            quantity=data.quantity,
            unit_price=data.unit_price,
            notes=data.notes,
            movement_date=movement_date,
        )
        await self.movement_repo.add(movement)

        # Update running stock on the product row
        product.stock_quantity = max(0.0, product.stock_quantity + data.quantity)
        await self.product_repo.update(product)

        logger.info(f"Stock updated: {product.name} {data.quantity:+g} → {product.stock_quantity}")
        return self._to_out(product)

    async def get_low_stock_alerts(self) -> list[ProductOut]:
        products = await self.product_repo.get_low_stock(self.shop_id)
        return [self._to_out(p) for p in products]

    def _to_out(self, product: Product) -> ProductOut:
        return ProductOut(
            id=product.id,
            name=product.name,
            name_hindi=product.name_hindi,
            aliases=product.aliases,
            category=product.category,
            unit=product.unit,
            selling_price=product.selling_price,
            stock_quantity=product.stock_quantity,
            shelf_location=product.shelf_location,
            location_notes=product.location_notes,
            is_active=product.is_active,
        )
