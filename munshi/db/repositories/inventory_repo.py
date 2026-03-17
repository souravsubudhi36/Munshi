"""Repository for products and stock movements."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from munshi.db.models import Product, StockMovement


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, product: Product) -> Product:
        self.session.add(product)
        await self.session.flush()
        await self.session.refresh(product)
        return product

    async def get_by_id(self, product_id: int) -> Product | None:
        result = await self.session.execute(
            select(Product).where(Product.id == product_id)
        )
        return result.scalar_one_or_none()

    async def get_by_barcode(self, barcode: str) -> Product | None:
        result = await self.session.execute(
            select(Product).where(Product.barcode == barcode)
        )
        return result.scalar_one_or_none()

    async def get_all_active(self, shop_id: int) -> list[Product]:
        result = await self.session.execute(
            select(Product)
            .where(Product.shop_id == shop_id, Product.is_active == True)  # noqa: E712
            .order_by(Product.name)
        )
        return list(result.scalars().all())

    async def get_low_stock(self, shop_id: int) -> list[Product]:
        result = await self.session.execute(
            select(Product).where(
                Product.shop_id == shop_id,
                Product.is_active == True,  # noqa: E712
                Product.stock_quantity <= Product.min_stock_alert,
            )
        )
        return list(result.scalars().all())

    async def update(self, product: Product) -> Product:
        await self.session.flush()
        await self.session.refresh(product)
        return product


class StockMovementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, movement: StockMovement) -> StockMovement:
        self.session.add(movement)
        await self.session.flush()
        await self.session.refresh(movement)
        return movement

    async def get_by_product(self, product_id: int, limit: int = 50) -> list[StockMovement]:
        result = await self.session.execute(
            select(StockMovement)
            .where(StockMovement.product_id == product_id)
            .order_by(StockMovement.movement_date.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
