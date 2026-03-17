"""SQLAlchemy ORM models for all Munshi entities."""

import json
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from munshi.db.database import Base


# ── Shop ──────────────────────────────────────────────────────────────────────

class Shop(Base):
    __tablename__ = "shop"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    owner_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    language: Mapped[str] = mapped_column(String(10), default="hi")
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# ── Ledger ────────────────────────────────────────────────────────────────────

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint("entry_type IN ('sale','expense','adjustment')", name="ck_ledger_type"),
        CheckConstraint("payment_mode IN ('cash','upi','card','credit')", name="ck_payment_mode"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shop.id"), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100))
    payment_mode: Mapped[str] = mapped_column(String(20), default="cash")
    recorded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    synced: Mapped[bool] = mapped_column(Boolean, default=False)
    remote_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# ── Customers ─────────────────────────────────────────────────────────────────

class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shop.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True)
    # JSON array of alternative names: ["Sharma ji", "Ramesh bhai"]
    aliases_json: Mapped[str] = mapped_column(Text, default="[]")
    address: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    synced: Mapped[bool] = mapped_column(Boolean, default=False)

    udhar_transactions: Mapped[list["UdharTransaction"]] = relationship(
        back_populates="customer", lazy="select"
    )

    @property
    def aliases(self) -> list[str]:
        return json.loads(self.aliases_json or "[]")

    @aliases.setter
    def aliases(self, value: list[str]) -> None:
        self.aliases_json = json.dumps(value, ensure_ascii=False)

    @property
    def all_names(self) -> list[str]:
        """All names including primary name, for fuzzy matching."""
        return [self.name] + self.aliases


# ── Udhar (Credit) ────────────────────────────────────────────────────────────

class UdharTransaction(Base):
    __tablename__ = "udhar_transactions"
    __table_args__ = (
        CheckConstraint(
            "transaction_type IN ('credit','payment')", name="ck_udhar_type"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shop.id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    # JSON: [{"name": "sugar", "qty": 2, "price": 40}]
    items_detail: Mapped[str | None] = mapped_column(Text)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    synced: Mapped[bool] = mapped_column(Boolean, default=False)
    remote_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    customer: Mapped["Customer"] = relationship(back_populates="udhar_transactions")


# ── Inventory ─────────────────────────────────────────────────────────────────

class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            "unit IN ('piece','kg','g','l','ml','dozen','pack')", name="ck_product_unit"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shop.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_hindi: Mapped[str | None] = mapped_column(String(200))
    # JSON array of aliases: ["maggi", "noodles", "2 minute noodles"]
    aliases_json: Mapped[str] = mapped_column(Text, default="[]")
    barcode: Mapped[str | None] = mapped_column(String(100), unique=True)
    category: Mapped[str | None] = mapped_column(String(100))
    unit: Mapped[str] = mapped_column(String(20), default="piece")
    purchase_price: Mapped[float | None] = mapped_column(Float)
    selling_price: Mapped[float | None] = mapped_column(Float)
    stock_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    min_stock_alert: Mapped[float] = mapped_column(Float, default=5.0)
    # Machine-readable location: "aisle-2, shelf-3, left"
    shelf_location: Mapped[str | None] = mapped_column(String(200))
    # Voice-friendly Hindi location: "chini ke paas, deewar ke paas"
    location_notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    synced: Mapped[bool] = mapped_column(Boolean, default=False)

    stock_movements: Mapped[list["StockMovement"]] = relationship(
        back_populates="product", lazy="select"
    )

    @property
    def aliases(self) -> list[str]:
        return json.loads(self.aliases_json or "[]")

    @aliases.setter
    def aliases(self, value: list[str]) -> None:
        self.aliases_json = json.dumps(value, ensure_ascii=False)

    @property
    def all_names(self) -> list[str]:
        names = [self.name]
        if self.name_hindi:
            names.append(self.name_hindi)
        names.extend(self.aliases)
        return names


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint(
            "movement_type IN ('purchase','sale','adjustment','wastage')",
            name="ck_movement_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shop.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Positive = stock in, negative = stock out
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    movement_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    synced: Mapped[bool] = mapped_column(Boolean, default=False)

    product: Mapped["Product"] = relationship(back_populates="stock_movements")


# ── Conversation Logs ─────────────────────────────────────────────────────────

class ConversationLog(Base):
    __tablename__ = "conversation_logs"
    __table_args__ = (
        CheckConstraint("role IN ('user','assistant','system')", name="ck_conv_role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shop.id"), nullable=False)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    transcript_raw: Mapped[str | None] = mapped_column(Text)
    intent: Mapped[str | None] = mapped_column(String(100))
    confidence: Mapped[float | None] = mapped_column(Float)
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ── Sync Queue ────────────────────────────────────────────────────────────────

class SyncQueueItem(Base):
    __tablename__ = "sync_queue"
    __table_args__ = (
        CheckConstraint(
            "operation IN ('insert','update','delete')", name="ck_sync_op"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_name: Mapped[str] = mapped_column(String(100), nullable=False)
    row_id: Mapped[int] = mapped_column(Integer, nullable=False)
    operation: Mapped[str] = mapped_column(String(20), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    queued_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    synced_at: Mapped[datetime | None] = mapped_column(DateTime)
