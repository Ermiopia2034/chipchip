from __future__ import annotations

import asyncio
import sys
import os
from datetime import datetime, date

# Ensure project root (/app) is on sys.path when executed as a script from /app/scripts
_HERE = os.path.dirname(__file__)
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


async def main() -> int:
    from app.services.db_service import DatabaseService
    from app.services.rag_service import VectorDBService
    import pandas as pd

    db = DatabaseService()

    ok = True
    messages: list[str] = []

    # 1) Row counts
    try:
        # Use direct SQL via SQLAlchemy text for counts to avoid model iteration
        from sqlalchemy import text
        from app.services.db_service import SessionLocal

        async with SessionLocal() as session:
            # Execute sequentially to avoid race
            products = int((await session.execute(text("SELECT COUNT(*) FROM products"))).scalar() or 0)
            users = int((await session.execute(text("SELECT COUNT(*) FROM users"))).scalar() or 0)
            inventory = int((await session.execute(text("SELECT COUNT(*) FROM inventory"))).scalar() or 0)
            orders = int((await session.execute(text("SELECT COUNT(*) FROM orders"))).scalar() or 0)
            order_items = int((await session.execute(text("SELECT COUNT(*) FROM order_items"))).scalar() or 0)
            competitor = int((await session.execute(text("SELECT COUNT(*) FROM competitor_pricing"))).scalar() or 0)
            tx = int((await session.execute(text("SELECT COUNT(*) FROM transaction_history"))).scalar() or 0)

        messages.append(
            f"Counts -> products={products}, users={users}, inventory={inventory}, orders={orders}, order_items={order_items}, competitor_pricing={competitor}, transaction_history={tx}"
        )
    except Exception as e:  # pragma: no cover - environment dependent
        ok = False
        messages.append(f"Count queries failed: {e}")

    # 2) Orphan checks
    try:
        from sqlalchemy import text
        from app.services.db_service import SessionLocal
        async with SessionLocal() as session:
            # order_items.product_id references products
            orphan_prod = int(
                (await session.execute(
                    text(
                        "SELECT COUNT(*) FROM order_items oi LEFT JOIN products p ON oi.product_id=p.product_id WHERE p.product_id IS NULL"
                    )
                )).scalar()
                or 0
            )
            # order_items.order_id references orders
            orphan_ord = int(
                (await session.execute(
                    text(
                        "SELECT COUNT(*) FROM order_items oi LEFT JOIN orders o ON oi.order_id=o.order_id WHERE o.order_id IS NULL"
                    )
                )).scalar()
                or 0
            )
            if orphan_prod or orphan_ord:
                ok = False
                messages.append(
                    f"Orphaned order_items detected: product_refs={orphan_prod}, order_refs={orphan_ord}"
                )
            else:
                messages.append("No orphaned order_items references detected")
    except Exception as e:  # pragma: no cover
        ok = False
        messages.append(f"Orphan check failed: {e}")

    # 3) Date validations
    try:
        from sqlalchemy import text
        from app.services.db_service import SessionLocal
        async with SessionLocal() as session:
            max_tx = (await session.execute(text("SELECT MAX(order_date) FROM transaction_history"))).scalar()
            if max_tx and isinstance(max_tx, datetime) and max_tx > datetime.utcnow():
                ok = False
                messages.append(f"Invalid future date in transaction_history: {max_tx}")
            else:
                messages.append("Transaction history dates valid (no future dates)")
    except Exception as e:  # pragma: no cover
        ok = False
        messages.append(f"Date validation failed: {e}")

    # 4) RAG knowledge base count vs CSV
    try:
        import os
        from app.config import settings
        csv_path = "/data/product_knowledge_base.csv"
        if not os.path.isfile(csv_path):
            messages.append("KB CSV not found at /data/product_knowledge_base.csv; skipping KB count validation")
        else:
            df = pd.read_csv(csv_path)
            expected = len(df)
            rag = VectorDBService()
            # Ensure collection exists
            rag._ensure_client()
            # Count entries in collection
            try:
                stored = rag.collection.count()  # type: ignore[attr-defined]
            except Exception:  # pragma: no cover - API variance
                # Fallback: attempt to query a large n and count
                q = rag.collection.get()  # type: ignore
                stored = len(q.get("ids") or [])
            # Accept minor drift; ensure at least expected-1 (allow one header skip variations)
            if stored >= expected - 1:
                messages.append(f"Chroma KB count ok: stored={stored}, expected≈{expected}")
            else:
                ok = False
                messages.append(
                    f"Chroma KB count too low: stored={stored}, expected≈{expected}. Consider re-ingesting."
                )
    except Exception as e:  # pragma: no cover
        ok = False
        messages.append(f"RAG validation failed: {e}")

    # Summary
    for m in messages:
        print(m)
    return 0 if ok else 2


if __name__ == "__main__":  # pragma: no cover
    rc = asyncio.run(main())
    sys.exit(rc)
