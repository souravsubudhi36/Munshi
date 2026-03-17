"""Repository for customers and udhar (credit) transactions."""

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from munshi.db.models import Customer, UdharTransaction


class CustomerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, customer: Customer) -> Customer:
        self.session.add(customer)
        await self.session.flush()
        await self.session.refresh(customer)
        return customer

    async def get_by_id(self, customer_id: int) -> Customer | None:
        result = await self.session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> Customer | None:
        result = await self.session.execute(
            select(Customer).where(Customer.phone == phone)
        )
        return result.scalar_one_or_none()

    async def get_all(self, shop_id: int) -> list[Customer]:
        result = await self.session.execute(
            select(Customer)
            .where(Customer.shop_id == shop_id)
            .order_by(Customer.name)
        )
        return list(result.scalars().all())

    async def update(self, customer: Customer) -> Customer:
        await self.session.flush()
        await self.session.refresh(customer)
        return customer


class UdharRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, txn: UdharTransaction) -> UdharTransaction:
        self.session.add(txn)
        await self.session.flush()
        await self.session.refresh(txn)
        return txn

    async def get_by_customer(self, customer_id: int) -> list[UdharTransaction]:
        result = await self.session.execute(
            select(UdharTransaction)
            .where(UdharTransaction.customer_id == customer_id)
            .order_by(UdharTransaction.transaction_date.desc())
        )
        return list(result.scalars().all())

    async def outstanding_per_customer(self, shop_id: int) -> list[dict]:
        """Returns list of {customer_id, customer_name, phone, outstanding_amount}."""
        result = await self.session.execute(
            select(
                Customer.id,
                Customer.name,
                Customer.phone,
                func.coalesce(
                    func.sum(
                        case(
                            (UdharTransaction.transaction_type == "credit", UdharTransaction.amount),
                            else_=-UdharTransaction.amount,
                        )
                    ),
                    0.0,
                ).label("outstanding"),
            )
            .outerjoin(UdharTransaction, UdharTransaction.customer_id == Customer.id)
            .where(Customer.shop_id == shop_id)
            .group_by(Customer.id)
            .order_by(func.coalesce(
                func.sum(
                    case(
                        (UdharTransaction.transaction_type == "credit", UdharTransaction.amount),
                        else_=-UdharTransaction.amount,
                    )
                ),
                0.0,
            ).desc())
        )
        return [
            {"customer_id": row[0], "customer_name": row[1], "phone": row[2], "outstanding": float(row[3])}
            for row in result.all()
        ]

    async def outstanding_for_customer(self, customer_id: int) -> float:
        result = await self.session.execute(
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (UdharTransaction.transaction_type == "credit", UdharTransaction.amount),
                            else_=-UdharTransaction.amount,
                        )
                    ),
                    0.0,
                )
            ).where(UdharTransaction.customer_id == customer_id)
        )
        return float(result.scalar() or 0.0)
