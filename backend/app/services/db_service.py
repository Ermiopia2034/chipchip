from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from difflib import SequenceMatcher

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, func, update, and_, or_, text
from sqlalchemy.orm import joinedload

from app.config import settings
from app.models.orm import (
    Base,
    User,
    Product,
    Inventory,
    Order,
    OrderItem,
    CompetitorPricing,
    TransactionHistory,
)
from app.services.exceptions import DatabaseError, RecordNotFoundError


def _async_db_url() -> str:
    url = settings.DATABASE_URL
    # Ensure asyncpg driver scheme
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


engine = create_async_engine(
    _async_db_url(),
    pool_size=10,
    max_overflow=20,
    future=True,
    echo=settings.DB_ECHO,
)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


class DatabaseService:
    def __init__(self):
        self._session_factory = SessionLocal

    # ---------- User operations ----------
    async def create_user(self, phone: str, name: Optional[str], user_type: str, location: Optional[str]) -> str:
        async with self._session_factory() as session:
            user = User(phone=phone, name=name, user_type=user_type, default_location=location)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return str(user.user_id)

    async def get_user_by_phone(self, phone: str) -> Optional[User]:
        async with self._session_factory() as session:
            res = await session.execute(select(User).where(User.phone == phone))
            return res.scalar_one_or_none()

    async def update_user(self, user_id: str, **kwargs) -> None:
        async with self._session_factory() as session:
            await session.execute(update(User).where(User.user_id == user_id).values(**kwargs))
            await session.commit()

    # ---------- Product operations ----------
    async def get_all_products(self) -> List[Product]:
        async with self._session_factory() as session:
            res = await session.execute(select(Product).order_by(Product.product_name))
            return list(res.scalars().all())

    async def get_product_by_name(self, name: str) -> Optional[Product]:
        async with self._session_factory() as session:
            # Case-insensitive equality using Python-lowered param
            res = await session.execute(
                select(Product).where(func.lower(Product.product_name) == name.lower())
            )
            return res.scalar_one_or_none()

    async def fuzzy_get_product_by_name(self, name: str, threshold: float = 0.8) -> Tuple[Optional[Product], float]:
        """
        Find the most similar product by name using a simple ratio. Returns (Product|None, score).
        Accepted when score >= threshold.
        """
        target = (name or "").strip().lower()
        if not target:
            return None, 0.0
        try:
            products = await self.get_all_products()
        except Exception:
            return None, 0.0
        best: Optional[Product] = None
        best_score: float = 0.0
        for p in products:
            cand = (p.product_name or "").strip().lower()
            if not cand:
                continue
            score = SequenceMatcher(None, target, cand).ratio()
            if score > best_score:
                best = p
                best_score = score
        if best_score >= threshold:
            return best, best_score
        return None, best_score

    async def search_products(self, query: str) -> List[Product]:
        async with self._session_factory() as session:
            pattern = f"%{query}%"
            # Support searching by product name OR category (e.g., "vegetables", "fruits", "dairy")
            res = await session.execute(
                select(Product).where(
                    or_(
                        Product.product_name.ilike(pattern),
                        Product.category.ilike(pattern),
                    )
                )
            )
            return list(res.scalars().all())

    # ---------- Inventory operations ----------
    async def add_inventory(
        self,
        supplier_id: str,
        product_id: int,
        quantity: float,
        price: float,
        available_date: date,
        expiry_date: Optional[date],
        image_url: Optional[str],
    ) -> int:
        async with self._session_factory() as session:
            inv = Inventory(
                supplier_id=supplier_id,
                product_id=product_id,
                quantity_kg=Decimal(str(quantity)),
                price_per_unit=Decimal(str(price)),
                available_date=available_date,
                expiry_date=expiry_date,
                image_url=image_url,
                status="active",
            )
            session.add(inv)
            await session.commit()
            await session.refresh(inv)
            return int(inv.inventory_id)

    async def get_available_inventory(self, product_id: int) -> List[Inventory]:
        today = date.today()
        async with self._session_factory() as session:
            res = await session.execute(
                select(Inventory)
                .where(
                    and_(
                        Inventory.product_id == product_id,
                        Inventory.status == "active",
                        Inventory.available_date <= today,
                    )
                )
                .options(joinedload(Inventory.product))
            )
            return list(res.scalars().all())

    async def get_supplier_inventory(self, supplier_id: str) -> List[Dict[str, Any]]:
        async with self._session_factory() as session:
            res = await session.execute(
                select(
                    Inventory.inventory_id,
                    Inventory.product_id,
                    Product.product_name,
                    Inventory.quantity_kg,
                    Inventory.price_per_unit,
                    Inventory.available_date,
                    Inventory.expiry_date,
                    Inventory.status,
                    Inventory.image_url,
                )
                .join(Product, Product.product_id == Inventory.product_id)
                .where(Inventory.supplier_id == supplier_id)
                .order_by(Inventory.available_date.desc())
            )
            rows = res.all()
            out: List[Dict[str, Any]] = []
            for r in rows:
                out.append(
                    {
                        "inventory_id": r.inventory_id,
                        "product_id": r.product_id,
                        "product_name": r.product_name,
                        "quantity_kg": float(r.quantity_kg),
                        "price_per_unit": float(r.price_per_unit),
                        "available_date": r.available_date,
                        "expiry_date": r.expiry_date,
                        "status": r.status,
                        "image_url": r.image_url,
                    }
                )
            return out

    async def check_expiring_inventory(self, supplier_id: str, days_threshold: int = 3) -> List[Dict[str, Any]]:
        async with self._session_factory() as session:
            cutoff = date.today() + timedelta(days=days_threshold)
            res = await session.execute(
                select(
                    Inventory.inventory_id,
                    Inventory.product_id,
                    Product.product_name,
                    Inventory.quantity_kg,
                    Inventory.price_per_unit,
                    Inventory.available_date,
                    Inventory.expiry_date,
                )
                .join(Product, Product.product_id == Inventory.product_id)
                .where(
                    and_(
                        Inventory.supplier_id == supplier_id,
                        Inventory.status == "active",
                        Inventory.expiry_date.is_not(None),
                        Inventory.expiry_date <= cutoff,
                    )
                )
            )
            return [
                {
                    "inventory_id": r.inventory_id,
                    "product_id": r.product_id,
                    "product_name": r.product_name,
                    "quantity_kg": float(r.quantity_kg),
                    "price_per_unit": float(r.price_per_unit),
                    "available_date": r.available_date,
                    "expiry_date": r.expiry_date,
                }
                for r in res.all()
            ]

    async def update_inventory_status(self, inventory_id: int, status: str) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(Inventory).where(Inventory.inventory_id == inventory_id).values(status=status)
            )
            await session.commit()

    # ---------- Order operations ----------
    async def create_order(
        self,
        customer_id: str,
        delivery_date: date,
        delivery_location: str,
        total_amount: float,
    ) -> str:
        async with self._session_factory() as session:
            order = Order(
                order_id=func.uuid_generate_v4(),  # server function
                customer_id=customer_id,
                delivery_date=delivery_date,
                delivery_location=delivery_location,
                total_amount=Decimal(str(total_amount)),
                status="pending",
            )
            # Insert via raw SQL to use uuid_generate_v4()
            res = await session.execute(
                text(
                    """
                    INSERT INTO orders (
                        order_id, customer_id, delivery_date, delivery_location, total_amount, status
                    ) VALUES (uuid_generate_v4(), :customer_id, :delivery_date, :delivery_location, :total_amount, 'pending')
                    RETURNING order_id
                    """
                ),
                {
                    "customer_id": customer_id,
                    "delivery_date": delivery_date,
                    "delivery_location": delivery_location,
                    "total_amount": float(total_amount),
                },
            )
            order_id = res.scalar_one()
            await session.commit()
            return str(order_id)

    async def add_order_items(self, order_id: str, items_list: List[Dict[str, Any]]) -> None:
        async with self._session_factory() as session:
            # Use executemany style insert
            values = [
                {
                    "order_id": order_id,
                    "product_id": it["product_id"],
                    "quantity_kg": float(it["quantity_kg"]),
                    "price_per_unit": float(it["price_per_unit"]),
                }
                for it in items_list
            ]
            await session.execute(
                text(
                    """
                    INSERT INTO order_items (order_id, product_id, quantity_kg, price_per_unit)
                    VALUES (:order_id, :product_id, :quantity_kg, :price_per_unit)
                    """
                ),
                values,
            )
            await session.commit()

    async def get_customer_orders(self, customer_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        async with self._session_factory() as session:
            stmt = select(Order).where(Order.customer_id == customer_id)
            if status:
                stmt = stmt.where(Order.status == status)
            res = await session.execute(stmt.order_by(Order.order_date.desc()))
            orders = res.scalars().all()

            # Fetch items for each order
            out: List[Dict[str, Any]] = []
            for o in orders:
                items_res = await session.execute(
                    select(OrderItem, Product.product_name)
                    .join(Product, Product.product_id == OrderItem.product_id)
                    .where(OrderItem.order_id == o.order_id)
                )
                items = [
                    {
                        "product_id": it.OrderItem.product_id,
                        "product_name": it.product_name,
                        "quantity_kg": float(it.OrderItem.quantity_kg),
                        "price_per_unit": float(it.OrderItem.price_per_unit),
                    }
                    for it in items_res.all()
                ]
                out.append(
                    {
                        "order_id": str(o.order_id),
                        "delivery_date": o.delivery_date,
                        "delivery_location": o.delivery_location,
                        "total_amount": float(o.total_amount),
                        "status": o.status,
                        "items": items,
                    }
                )
            return out

    async def get_supplier_pending_orders(self, supplier_id: str) -> List[Dict[str, Any]]:
        async with self._session_factory() as session:
            res = await session.execute(
                select(Order).where(and_(Order.supplier_id == supplier_id, Order.status == "pending"))
            )
            return [
                {
                    "order_id": str(o.order_id),
                    "delivery_date": o.delivery_date,
                    "delivery_location": o.delivery_location,
                    "total_amount": float(o.total_amount),
                }
                for o in res.scalars().all()
            ]

    async def update_order_status(self, order_id: str, status: str, supplier_id: Optional[str] = None) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(Order).where(Order.order_id == order_id).values(status=status, supplier_id=supplier_id)
            )
            await session.commit()

    async def get_supplier_schedule(
        self, supplier_id: str, start_date: date, end_date: date
    ) -> List[Dict[str, Any]]:
        async with self._session_factory() as session:
            res = await session.execute(
                select(Order)
                .where(
                    and_(
                        Order.supplier_id == supplier_id,
                        Order.status == "confirmed",
                        Order.delivery_date >= start_date,
                        Order.delivery_date <= end_date,
                    )
                )
                .order_by(Order.delivery_date.asc())
            )
            return [
                {
                    "order_id": str(o.order_id),
                    "delivery_date": o.delivery_date,
                    "delivery_location": o.delivery_location,
                    "total_amount": float(o.total_amount),
                }
                for o in res.scalars().all()
            ]

    # ---------- Pricing insights ----------
    async def get_competitor_prices(self, product_id: int, days_back: int = 30) -> List[Dict[str, Any]]:
        start = date.today() - timedelta(days=days_back)
        async with self._session_factory() as session:
            res = await session.execute(
                select(
                    CompetitorPricing.date,
                    CompetitorPricing.price,
                    CompetitorPricing.source_market_type,
                ).where(
                    and_(CompetitorPricing.product_id == product_id, CompetitorPricing.date >= start)
                )
            )
            return [
                {
                    "date": r.date,
                    "price": float(r.price),
                    "source_market_type": r.source_market_type,
                }
                for r in res.all()
            ]

    async def get_average_competitor_price(
        self, product_id: int, market_type: str, days_back: int = 30
    ) -> Optional[float]:
        start = date.today() - timedelta(days=days_back)
        async with self._session_factory() as session:
            res = await session.execute(
                select(func.avg(CompetitorPricing.price)).where(
                    and_(
                        CompetitorPricing.product_id == product_id,
                        CompetitorPricing.source_market_type == market_type,
                        CompetitorPricing.date >= start,
                    )
                )
            )
            avg_val = res.scalar()
            return float(avg_val) if avg_val is not None else None

    async def get_average_competitor_price_anytime(self, product_id: int, market_type: str) -> Optional[float]:
        async with self._session_factory() as session:
            res = await session.execute(
                select(func.avg(CompetitorPricing.price)).where(
                    and_(
                        CompetitorPricing.product_id == product_id,
                        CompetitorPricing.source_market_type == market_type,
                    )
                )
            )
            avg_val = res.scalar()
            return float(avg_val) if avg_val is not None else None

    async def get_historical_transaction_prices(self, product_id: int, days_back: int = 60) -> Optional[float]:
        start_dt = datetime.utcnow() - timedelta(days=days_back)
        async with self._session_factory() as session:
            res = await session.execute(
                select(func.avg(TransactionHistory.price_per_unit)).where(
                    and_(
                        TransactionHistory.product_id == product_id,
                        TransactionHistory.order_date >= start_dt,
                    )
                )
            )
            avg_val = res.scalar()
            return float(avg_val) if avg_val is not None else None

    async def calculate_pricing_recommendation(self, product_id: int) -> Dict[str, Any]:
        async def _avg_with_fallback(market: str) -> Optional[float]:
            # Try recent windows, then all-time
            for days in (30, 90, 180, 365):
                val = await self.get_average_competitor_price(product_id, market, days_back=days)
                if val is not None:
                    return val
            return await self.get_average_competitor_price_anytime(product_id, market)

        farm = await _avg_with_fallback("Farm")
        supermarket = await _avg_with_fallback("Supermarket")
        distribution = await _avg_with_fallback("Distribution Center")
        historical = await self.get_historical_transaction_prices(product_id)

        # Simple rule: Farm avg + 10% as baseline
        base = farm if farm is not None else historical if historical is not None else 0.0
        recommended = round(base * 1.10, 2) if base else None

        # Get product name
        async with self._session_factory() as session:
            res = await session.execute(select(Product.product_name).where(Product.product_id == product_id))
            name = res.scalar_one_or_none()

        return {
            "product_id": product_id,
            "product_name": name,
            "recommended": recommended if recommended is not None else 0.0,
            "farm_avg": farm,
            "supermarket_avg": supermarket,
            "distribution_avg": distribution,
            "historical_avg": historical,
        }
