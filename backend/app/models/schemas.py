from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    phone: str
    name: Optional[str] = None
    user_type: str = Field(default="customer")
    default_location: Optional[str] = None


class UserOut(BaseModel):
    user_id: str
    phone: str
    name: Optional[str] = None
    user_type: str
    default_location: Optional[str] = None


class ProductOut(BaseModel):
    product_id: int
    product_name: str
    category: Optional[str] = None
    unit: Optional[str] = None


class InventoryCreate(BaseModel):
    product_id: int
    quantity_kg: float
    price_per_unit: float
    available_date: date
    expiry_date: Optional[date] = None
    image_url: Optional[str] = None


class InventoryOut(BaseModel):
    inventory_id: int
    product_id: int
    product_name: Optional[str] = None
    quantity_kg: float
    price_per_unit: float
    available_date: date
    expiry_date: Optional[date] = None
    status: str
    image_url: Optional[str] = None


class OrderItemIn(BaseModel):
    product_id: int
    quantity_kg: float
    price_per_unit: float


class OrderCreate(BaseModel):
    customer_id: str
    delivery_date: date
    delivery_location: str
    total_amount: float
    items: List[OrderItemIn]


class OrderOut(BaseModel):
    order_id: str
    customer_id: str
    delivery_date: date
    delivery_location: str
    total_amount: float
    status: str


class PricingRecommendation(BaseModel):
    product_id: int
    product_name: Optional[str] = None
    recommended: float
    farm_avg: Optional[float] = None
    supermarket_avg: Optional[float] = None
    distribution_avg: Optional[float] = None
    historical_avg: Optional[float] = None


class SessionData(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    user_type: str = "unknown"
    registered: bool = False
    phone: Optional[str] = None
    name: Optional[str] = None
    default_location: Optional[str] = None
    context: dict = Field(default_factory=dict)
    conversation_history: list = Field(default_factory=list)
    language: str = "auto"
    created_at: Optional[str] = None
    last_active: Optional[str] = None

