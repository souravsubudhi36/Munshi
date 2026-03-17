"""Udhar (credit) service — customer credit tracking with fuzzy name matching."""

import json

import pendulum
from loguru import logger
from rapidfuzz import process as fuzz_process
from sqlalchemy.ext.asyncio import AsyncSession

from munshi.db.models import Customer, UdharTransaction
from munshi.db.repositories.udhar_repo import CustomerRepository, UdharRepository
from munshi.modules.udhar.schemas import (
    CreditInput,
    CustomerOut,
    NewCustomerInput,
    OutstandingResult,
    PaymentInput,
    UdharTransactionOut,
)

# Minimum fuzzy match score (0-100) to consider a customer match
FUZZY_THRESHOLD = 65


def _today():
    return pendulum.today("Asia/Kolkata").date()


class UdharService:
    def __init__(self, session: AsyncSession, shop_id: int) -> None:
        self.session = session
        self.customer_repo = CustomerRepository(session)
        self.udhar_repo = UdharRepository(session)
        self.shop_id = shop_id

    async def _find_customer(self, name: str) -> list[tuple[Customer, float]]:
        """
        Fuzzy-match a name against all customers.
        Returns list of (customer, score) sorted by score desc.
        """
        all_customers = await self.customer_repo.get_all(self.shop_id)
        if not all_customers:
            return []

        # Build flat list of (customer, alias_name) pairs
        candidates: list[tuple[Customer, str]] = []
        for c in all_customers:
            for alias in c.all_names:
                candidates.append((c, alias))

        alias_strings = [alias for _, alias in candidates]
        matches = fuzz_process.extract(name, alias_strings, limit=5)

        seen_ids: set[int] = set()
        results: list[tuple[Customer, float]] = []
        for matched_str, score, idx in matches:
            if score < FUZZY_THRESHOLD:
                continue
            customer = candidates[idx][0]
            if customer.id not in seen_ids:
                seen_ids.add(customer.id)
                results.append((customer, score))

        return results

    async def add_credit(self, data: CreditInput) -> tuple[UdharTransactionOut, CustomerOut]:
        """Add a credit (goods taken on udhar) transaction."""
        matches = await self._find_customer(data.customer_name)

        if not matches:
            raise ValueError(f"No customer found matching '{data.customer_name}'. Create them first.")

        customer, score = matches[0]
        if score < 90 and len(matches) > 1:
            # Ambiguous — caller should ask user to disambiguate
            names = [c.name for c, _ in matches[:3]]
            raise AmbiguousCustomerError(
                f"Multiple customers match '{data.customer_name}': {names}",
                candidates=names,
            )

        txn_date = data.transaction_date or _today()
        items_json = json.dumps([i.model_dump() for i in data.items], ensure_ascii=False) if data.items else None

        txn = UdharTransaction(
            shop_id=self.shop_id,
            customer_id=customer.id,
            transaction_type="credit",
            amount=data.amount,
            description=data.description,
            items_detail=items_json,
            transaction_date=txn_date,
        )
        saved_txn = await self.udhar_repo.add(txn)
        outstanding = await self.udhar_repo.outstanding_for_customer(customer.id)

        logger.info(f"Udhar credit: {customer.name} ₹{data.amount} (total outstanding: ₹{outstanding})")
        return (
            UdharTransactionOut.model_validate(saved_txn),
            CustomerOut(
                id=customer.id,
                name=customer.name,
                phone=customer.phone,
                aliases=customer.aliases,
                outstanding_amount=outstanding,
            ),
        )

    async def record_payment(self, data: PaymentInput) -> tuple[UdharTransactionOut, CustomerOut]:
        """Record a payment received from a credit customer."""
        matches = await self._find_customer(data.customer_name)
        if not matches:
            raise ValueError(f"No customer found matching '{data.customer_name}'.")

        customer, score = matches[0]
        if score < 90 and len(matches) > 1:
            names = [c.name for c, _ in matches[:3]]
            raise AmbiguousCustomerError(
                f"Multiple customers match '{data.customer_name}': {names}",
                candidates=names,
            )

        txn_date = data.transaction_date or _today()
        txn = UdharTransaction(
            shop_id=self.shop_id,
            customer_id=customer.id,
            transaction_type="payment",
            amount=data.amount,
            description=data.description,
            transaction_date=txn_date,
        )
        saved_txn = await self.udhar_repo.add(txn)
        outstanding = await self.udhar_repo.outstanding_for_customer(customer.id)

        logger.info(f"Udhar payment: {customer.name} ₹{data.amount} (remaining: ₹{outstanding})")
        return (
            UdharTransactionOut.model_validate(saved_txn),
            CustomerOut(
                id=customer.id,
                name=customer.name,
                phone=customer.phone,
                aliases=customer.aliases,
                outstanding_amount=outstanding,
            ),
        )

    async def get_outstanding(self, customer_name: str | None = None) -> list[OutstandingResult]:
        """
        Get outstanding balances.
        If customer_name given, return just that customer.
        Otherwise return all customers with non-zero outstanding.
        """
        if customer_name:
            matches = await self._find_customer(customer_name)
            if not matches:
                raise ValueError(f"No customer found matching '{customer_name}'.")
            customer, _ = matches[0]
            outstanding = await self.udhar_repo.outstanding_for_customer(customer.id)
            txns_raw = await self.udhar_repo.get_by_customer(customer.id)
            return [OutstandingResult(
                customer_id=customer.id,
                customer_name=customer.name,
                phone=customer.phone,
                outstanding_amount=outstanding,
                transactions=[UdharTransactionOut.model_validate(t) for t in txns_raw[:10]],
            )]
        else:
            all_outstanding = await self.udhar_repo.outstanding_per_customer(self.shop_id)
            return [
                OutstandingResult(
                    customer_id=row["customer_id"],
                    customer_name=row["customer_name"],
                    phone=row["phone"],
                    outstanding_amount=row["outstanding"],
                )
                for row in all_outstanding
                if row["outstanding"] > 0
            ]

    async def create_customer(self, data: NewCustomerInput) -> CustomerOut:
        customer = Customer(
            shop_id=self.shop_id,
            name=data.name,
            phone=data.phone,
            address=data.address,
        )
        customer.aliases = data.aliases
        saved = await self.customer_repo.add(customer)
        logger.info(f"New customer created: {data.name}")
        return CustomerOut(
            id=saved.id,
            name=saved.name,
            phone=saved.phone,
            aliases=saved.aliases,
            outstanding_amount=0.0,
        )


class AmbiguousCustomerError(ValueError):
    """Raised when multiple customers match a name — caller must disambiguate."""

    def __init__(self, message: str, candidates: list[str]) -> None:
        super().__init__(message)
        self.candidates = candidates
