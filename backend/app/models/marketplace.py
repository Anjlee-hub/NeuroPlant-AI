"""Marketplace models (M4, Task 1).

Two content tables power the farmer marketplace:

* :class:`CropListing` — a farmer's produce offered for sale. Owned by the
  listing farmer (``farmer_id`` → ``users.id``) and filtered/indexed on the
  fields customers actually browse (category, availability, farmer).
* :class:`Product` — an agricultural input sold by a shop (fertilizers,
  pesticides, seeds, tools). Owned by the seller user (``seller_id`` →
  ``users.id``) whose shop profile is the ``SellerProfile`` row created at
  registration.

The shop itself is *not* a new table — the existing ``SellerProfile`` (M1)
already models an agricultural shop (``shop_name``/``address``/``verified``);
Task 1 extends it with the marketplace fields the requirement lists
(phone, delivery availability, rating) instead of duplicating a seller table.
Portable types only (String / JSON / Float / Boolean / DateTime), the same
convention as every other model, so PostgreSQL (prod) and SQLite (native dev)
both work.
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin


class CropListing(Base, TimestampMixin):
    __tablename__ = "crop_listings"
    __table_args__ = (
        # Customers browse by category and availability — index both.
        Index("ix_crop_listings_category", "category"),
        Index("ix_crop_listings_availability", "availability"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    farmer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    crop_name: Mapped[str] = mapped_column(String(120), nullable=False)
    # vegetable | fruit | grain | pulses | spice | other (app-level validation).
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    variety: Mapped[str | None] = mapped_column(String(120), nullable=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    # kg | g | qtl | bag | dozen | piece | l | box | bundle (app-level validation).
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)  # per unit
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    images: Mapped[list | None] = mapped_column(JSON, nullable=True)
    harvest_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    organic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # available | limited | sold_out | archived (app-level validation; the
    # archived status is an M4 Task 2 additive extension for retiring a
    # listing without deleting it).
    availability: Mapped[str] = mapped_column(String(20), default="available", nullable=False)


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (
        # Customers browse by category and availability — index both.
        Index("ix_products_category", "category"),
        Index("ix_products_availability", "availability"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # The shop is the seller's ``SellerProfile``; products key off the seller
    # user id (denormalized, same pattern as ``RecoveryLog.user_id``) so every
    # product op reuses the direct ownership guard.
    seller_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # fertilizer | pesticide | seed | tool | organic (app-level validation).
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(120), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    images: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # ── Seller Portal fields (M4, Task 4) ──────────────────────────────────
    organic: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    manufacturer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    usage_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    # in_stock | out_of_stock | archived (app-level validation). ``archived``
    # retires a product without deleting it (same semantics as crop listings);
    # in/out of stock drives the seller dashboard's stock toggle.
    availability: Mapped[str] = mapped_column(
        String(20), default="in_stock", server_default=text("'in_stock'"), nullable=False
    )
