import asyncio
import pytest


@pytest.mark.asyncio
async def test_db_service_import_and_methods_exist():
    from app.services.db_service import DatabaseService

    db = DatabaseService()
    # Ensure methods are callable
    assert hasattr(db, "get_all_products")
    assert hasattr(db, "search_products")
    assert hasattr(db, "calculate_pricing_recommendation")

