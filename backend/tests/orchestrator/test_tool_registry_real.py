import os
import time
import asyncio
import pytest


pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
async def test_tool_registry_rag_and_inventory_flow(db_serialized):
    from app.orchestrator.session_manager import SessionManager
    from app.orchestrator.tool_registry import ToolRegistry
    from app.services.db_service import DatabaseService
    import asyncio

    # Ensure DB reachable first, delay ToolRegistry init until after DB ops
    db = DatabaseService()
    sm = SessionManager()

    # Prepare supplier session and DB user (yield to avoid connection overlap)
    sid = await sm.create_session()
    phone = os.getenv("TEST_SUPPLIER_PHONE") or f"09{int(time.time()) % 10}{int(time.time()*1000) % 9999999:07d}"
    await asyncio.sleep(0.05)
    new_user_id = await db.create_user(phone=phone, name="Supplier Test", user_type="supplier", location="Addis Ababa")
    await sm.update_session(sid, {"registered": True, "user_type": "supplier", "user_id": new_user_id})

    # Pick any existing product for inventory
    prods = await db.get_all_products()
    assert prods, "Products must be loaded in DB"
    pname = prods[0].product_name

    # Initialize tools only after DB steps to avoid asyncpg transaction overlap
    tools = ToolRegistry()

    add_res = await tools.add_inventory_handler(
        {
            "product_name": pname,
            "quantity_kg": 5.0,
            "price_per_unit": 50.0,
            "available_date": os.getenv("TEST_AVAILABLE_DATE", "2025-01-01"),
            "generate_image": False,
        },
        session_id=sid,
    )
    assert add_res["success"] is True

    # Check stock returns at least one item
    stock = await tools.check_supplier_stock_handler({}, session_id=sid)
    assert stock["success"] is True
    assert isinstance(stock["data"], list)
    assert len(stock["data"]) >= 1

    # Finally validate RAG returns results (after tool init, to avoid concurrency flap)
    rag_res = await tools.rag_query_handler({"query": "storage", "category": "storage"}, session_id=None)
    assert rag_res["success"] is True
    assert isinstance(rag_res["data"], list)
    assert len(rag_res["data"]) >= 1
