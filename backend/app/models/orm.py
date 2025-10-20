from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Date,
    Integer,
    Numeric,
    ForeignKey,
    Text,
    Enum,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    phone = Column(String(15), unique=True, nullable=False)
    name = Column(String(100))
    user_type = Column(String(20), nullable=False, default="customer")
    default_location = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships (optional for queries)
    inventory = relationship("Inventory", back_populates="supplier", lazy="selectin")


class Product(Base):
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True, autoincrement=True)
    product_name = Column(String(100), nullable=False, unique=True)
    category = Column(String(50))
    unit = Column(String(20))


class Inventory(Base):
    __tablename__ = "inventory"

    inventory_id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    product_id = Column(Integer, ForeignKey("products.product_id"))
    quantity_kg = Column(Numeric(10, 2), nullable=False)
    price_per_unit = Column(Numeric(10, 2), nullable=False)
    available_date = Column(Date, nullable=False)
    expiry_date = Column(Date)
    image_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), nullable=False, default="active")

    supplier = relationship("User", back_populates="inventory", lazy="selectin")
    product = relationship("Product", lazy="selectin")


class Order(Base):
    __tablename__ = "orders"

    order_id = Column(UUID(as_uuid=True), primary_key=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    order_date = Column(DateTime, default=datetime.utcnow)
    delivery_date = Column(Date, nullable=False)
    delivery_location = Column(String(200), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    payment_method = Column(String(20), nullable=False, default="COD")
    created_at = Column(DateTime, default=datetime.utcnow)


class OrderItem(Base):
    __tablename__ = "order_items"

    item_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.order_id", ondelete="CASCADE"))
    product_id = Column(Integer, ForeignKey("products.product_id"))
    quantity_kg = Column(Numeric(10, 2), nullable=False)
    price_per_unit = Column(Numeric(10, 2), nullable=False)
    # subtotal is generated column in DB; SQLAlchemy can compute if needed


class CompetitorPricing(Base):
    __tablename__ = "competitor_pricing"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    product_id = Column(Integer, ForeignKey("products.product_id"))
    product_name = Column(String(100))
    price = Column(Numeric(10, 2), nullable=False)
    source_market_type = Column(String(50))
    location_detail = Column(String(100))


class TransactionHistory(Base):
    __tablename__ = "transaction_history"

    transaction_id = Column(Integer, primary_key=True, autoincrement=True)
    order_date = Column(DateTime, nullable=False)
    product_id = Column(Integer, ForeignKey("products.product_id"))
    product_name = Column(String(100))
    quantity_ordered = Column(Numeric(10, 2))
    price_per_unit = Column(Numeric(10, 2))
    order_total_amount = Column(Numeric(10, 2))
