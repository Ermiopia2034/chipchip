import os
import time
from datetime import date, timedelta

import pytest


pytestmark = pytest.mark.asyncio


async def _ensure_db_ready():
    try:
        from app.services.db_service import DatabaseService

        db = DatabaseService()
        prods = await db.get_all_products()
        assert prods, "Products table must be populated (run dataset loader)."
        return db, prods
    except Exception as e:  # pragma: no cover - environment dependent
        pytest.skip(f"Database not reachable or uninitialized: {e}")


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set for LLM-backed flows"
)
async def test_customer_registration_rag_and_order_flow():
    """
    End-to-end: register customer via chat, ask a RAG question, and place an order
    via tool handler. Uses real LLM (Gemini) and real Chroma/DB.
    """
    from app.orchestrator.session_manager import SessionManager
    from app.orchestrator.conversation import ConversationOrchestrator
    from app.orchestrator.tool_registry import ToolRegistry

    db, prods = await _ensure_db_ready()
    product = prods[0]

    # Prepare inventory so ordering can succeed
    supplier_phone = f"09{int(time.time()) % 10}{int(time.time()*1000) % 9999999:07d}"
    supplier_id = await db.create_user(
        phone=supplier_phone,
        name="Supplier IT",
        user_type="supplier",
        location="Addis Ababa",
    )
    today = date.today()
    await db.add_inventory(
        supplier_id=supplier_id,
        product_id=product.product_id,
        quantity=25.0,
        price=55.0,
        available_date=today,
        expiry_date=today + timedelta(days=10),
        image_url=None,
    )

    sm = SessionManager()
    sid = await sm.create_session()
    orch = ConversationOrchestrator(sessions=sm)

    # Registration in one message to satisfy intent heuristics
    cust_phone = f"09{int(time.time_ns()) % 100000000:08d}"
    r1 = await orch.process_message(
        sid, f"My name is Abebe, phone {cust_phone}, I live in Addis Ababa"
    )
    assert r1["type"] == "text" and "registered" in r1["content"].lower()

    # RAG query
    r2 = await orch.process_message(sid, "How do I store tomatoes?")
    assert r2["type"] == "text"
    assert isinstance(r2.get("content"), str) and len(r2["content"]) > 0

    # Order via tool registry for determinism (LLM may vary in tool-calling)
    tools = ToolRegistry()
    delivery = (today + timedelta(days=2)).isoformat()
    args = {
        "items": [{"product_name": product.product_name, "quantity_kg": 2.0}],
        "delivery_date": delivery,
        "delivery_location": "Bole, Addis Ababa",
    }
    res = await tools.create_order_handler(args, session_id=sid)
    assert res["success"] is True and "order_id" in (res["data"] or {})


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set for LLM-backed flows"
)
async def test_supplier_inventory_pricing_and_image_flow():
    """
    End-to-end: register supplier via chat, add inventory with pricing insights and
    request image generation. Uses real LLM and image model.
    """
    from app.orchestrator.session_manager import SessionManager
    from app.orchestrator.conversation import ConversationOrchestrator
    from app.orchestrator.tool_registry import ToolRegistry

    db, prods = await _ensure_db_ready()
    pname = prods[0].product_name

    sm = SessionManager()
    sid = await sm.create_session()
    orch = ConversationOrchestrator(sessions=sm)

    # Supplier registration message
    supp_phone = f"09{(int(time.time_ns()) + 1) % 100000000:08d}"
    r1 = await orch.process_message(
        sid, f"I'm a supplier, name Kebede, phone {supp_phone}, location Addis Ababa"
    )
    assert r1["type"] == "text" and "registered" in r1["content"].lower()

    tools = ToolRegistry()
    # Pricing insights
    pi = await tools.get_pricing_insights_handler({"product_name": pname}, session_id=sid)
    assert pi["success"] is True and "Recommendation" in pi["message"]

    # Add inventory with image generation
    today = date.today()
    add_res = await tools.add_inventory_handler(
        {
            "product_name": pname,
            "quantity_kg": 5.0,
            "price_per_unit": 50.0,
            "available_date": today.isoformat(),
            "expiry_date": (today + timedelta(days=10)).isoformat(),
            "generate_image": True,
        },
        session_id=sid,
    )
    assert add_res["success"] is True
    # If model responds, an image URL should be present; if not, message still indicates addition
    assert (add_res["data"] or {}).get("inventory_id") is not None


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set for LLM-backed flows"
)
async def test_flash_sale_suggestion_flow():
    """
    Create near-expiry inventory for a supplier and ask for flash-sale suggestions.
    """
    from app.orchestrator.session_manager import SessionManager
    from app.orchestrator.tool_registry import ToolRegistry
    from app.services.db_service import DatabaseService

    db, prods = await _ensure_db_ready()
    pname = prods[0].product_name

    sm = SessionManager()
    sid = await sm.create_session()

    # Create supplier user and attach to session
    supplier_phone = f"09{int(time.time()) % 10}{int(time.time()*1000) % 9999999:07d}"
    supplier_id = await db.create_user(
        phone=supplier_phone, name="Supplier FS", user_type="supplier", location="Addis"
    )
    await sm.update_session(sid, {"registered": True, "user_type": "supplier", "user_id": supplier_id})

    # Add inventory expiring tomorrow
    today = date.today()
    product = await db.get_product_by_name(pname)
    assert product is not None
    await db.add_inventory(
        supplier_id=supplier_id,
        product_id=product.product_id,
        quantity=10.0,
        price=50.0,
        available_date=today,
        expiry_date=today + timedelta(days=1),
        image_url=None,
    )

    tools = ToolRegistry()
    res = await tools.suggest_flash_sale_handler({"days_threshold": 3}, session_id=sid)
    assert res["success"] is True
    assert "Expiring" in res["message"] or "expiring" in res["message"].lower() or isinstance(res["data"], list)


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set for LLM-backed flows"
)
async def test_multilanguage_basic():
    """
    Send English and Amharic messages; ensure responses are generated without error.
    """
    from app.orchestrator.session_manager import SessionManager
    from app.orchestrator.conversation import ConversationOrchestrator

    sm = SessionManager()
    sid = await sm.create_session()
    orch = ConversationOrchestrator(sessions=sm)

    r1 = await orch.process_message(sid, "Hello")
    assert r1["type"] == "text" and isinstance(r1.get("content"), str)

    r2 = await orch.process_message(sid, "ሰላም")
    assert r2["type"] == "text" and isinstance(r2.get("content"), str)
