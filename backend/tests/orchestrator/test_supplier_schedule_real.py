import time
from datetime import date, timedelta

import pytest


pytestmark = pytest.mark.asyncio


async def _ensure_db_ready():
    try:
        from app.services.db_service import DatabaseService

        db = DatabaseService()
        prods = await db.get_all_products()
        return db, prods
    except Exception as e:  # pragma: no cover - environment dependent
        pytest.skip(f"Database not reachable or uninitialized: {e}")


@pytest.mark.asyncio
async def test_supplier_schedule_listing_real(db_serialized):
    """
    Real-data integration: create confirmed orders for a supplier and verify
    ToolRegistry.get_supplier_schedule_handler aggregates the current week.
    """
    from app.orchestrator.session_manager import SessionManager
    from app.orchestrator.tool_registry import ToolRegistry
    from app.services.db_service import DatabaseService

    db, prods = await _ensure_db_ready()
    assert prods, "Products must be seeded"
    product = prods[0]

    # Create supplier and customer
    supplier_phone = f"09{int(time.time()) % 10}{int(time.time()*1000) % 9999999:07d}"
    customer_phone = f"09{(int(time.time())+2) % 10}{int(time.time()*1000) % 9999999:07d}"
    supplier_id = await db.create_user(
        phone=supplier_phone,
        name="Supplier Sched",
        user_type="supplier",
        location="Addis Ababa",
    )
    customer_id = await db.create_user(
        phone=customer_phone,
        name="Customer Sched",
        user_type="customer",
        location="Addis Ababa",
    )

    # Seed at least one inventory (not strictly required for schedule, but realistic)
    today = date.today()
    await db.add_inventory(
        supplier_id=supplier_id,
        product_id=product.product_id,
        quantity=5.0,
        price=55.0,
        available_date=today,
        expiry_date=today + timedelta(days=7),
        image_url=None,
    )

    # Create two orders for current week and confirm them for the supplier
    start_week = today - timedelta(days=today.weekday())
    d1 = start_week + timedelta(days=1)
    d2 = start_week + timedelta(days=3)

    oid1 = await db.create_order(customer_id, d1, "Bole, Addis Ababa", 100.0)
    await db.add_order_items(oid1, [{"product_id": product.product_id, "quantity_kg": 1.0, "price_per_unit": 50.0}])
    await db.update_order_status(oid1, "confirmed", supplier_id=supplier_id)

    oid2 = await db.create_order(customer_id, d2, "CMC, Addis Ababa", 150.0)
    await db.add_order_items(oid2, [{"product_id": product.product_id, "quantity_kg": 2.0, "price_per_unit": 50.0}])
    await db.update_order_status(oid2, "confirmed", supplier_id=supplier_id)

    # Supplier session
    sm = SessionManager()
    sid = await sm.create_session()
    await sm.update_session(sid, {"registered": True, "user_type": "supplier", "user_id": supplier_id})

    tools = ToolRegistry()
    res = await tools.get_supplier_schedule_handler({}, session_id=sid)

    assert res["success"] is True
    assert isinstance(res["data"], list)
    assert len(res["data"]) >= 1
    assert "Your Delivery Schedule:" in res["message"] or res["message"].startswith("Your Delivery Schedule:")
