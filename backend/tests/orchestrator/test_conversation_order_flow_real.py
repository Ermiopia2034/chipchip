import os
import time
from datetime import date, timedelta

import pytest


pytestmark = pytest.mark.asyncio


async def _ensure_db_ready():
    """Best-effort check that DB is reachable; skip test if not."""
    try:
        from app.services.db_service import DatabaseService

        db = DatabaseService()
        # simple query
        prods = await db.get_all_products()
        return db, prods
    except Exception as e:  # pragma: no cover - environment dependent
        pytest.skip(f"Database not reachable or uninitialized: {e}")


async def _pick_product_with_fallback(db):
    prods = await db.get_all_products()
    assert prods, "Products table must be populated (run dataset loader)."
    return prods[0]


@pytest.mark.asyncio
async def test_customer_order_flow_tool_registry_real(db_serialized):
    """
    Real-data integration: create supplier inventory, register a customer session,
    and place an order via ToolRegistry.create_order_handler.

    This test does not require LLM; it exercises DB + tool handler end-to-end.
    """
    from app.orchestrator.session_manager import SessionManager
    from app.orchestrator.tool_registry import ToolRegistry
    from app.services.db_service import DatabaseService

    # Ensure DB is reachable and products exist
    db, _ = await _ensure_db_ready()

    # Prepare a supplier with inventory for an existing product
    product = await _pick_product_with_fallback(db)
    supplier_phone = f"09{int(time.time()) % 10}{int(time.time()*1000) % 9999999:07d}"
    supplier_id = await db.create_user(
        phone=supplier_phone,
        name="Supplier E2E",
        user_type="supplier",
        location="Addis Ababa",
    )
    today = date.today()
    await db.add_inventory(
        supplier_id=supplier_id,
        product_id=product.product_id,
        quantity=10.0,
        price=50.0,
        available_date=today,
        expiry_date=today + timedelta(days=10),
        image_url=None,
    )

    # Create a customer session and user
    sm = SessionManager()
    sid = await sm.create_session()
    customer_phone = f"09{(int(time.time())+1) % 10}{int(time.time()*1000) % 9999999:07d}"
    customer_id = await db.create_user(
        phone=customer_phone,
        name="Customer E2E",
        user_type="customer",
        location="Bole, Addis Ababa",
    )
    await sm.update_session(
        sid,
        {
            "registered": True,
            "user_type": "customer",
            "user_id": customer_id,
            "name": "Customer E2E",
            "default_location": "Bole, Addis Ababa",
        },
    )

    tools = ToolRegistry()
    delivery = (today + timedelta(days=2)).isoformat()
    args = {
        "items": [{"product_name": product.product_name, "quantity_kg": 1.0}],
        "delivery_date": delivery,
        "delivery_location": "Bole, Addis Ababa",
    }
    res = await tools.create_order_handler(args, session_id=sid)

    assert res["success"] is True
    assert "order_id" in (res["data"] or {})
    assert "Total:" in res["message"] or "Total:" in ""  # message formatting present

    # Verify order appears for customer
    orders = await db.get_customer_orders(customer_id)
    assert any(o.get("order_id") == res["data"]["order_id"] for o in orders)
