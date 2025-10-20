#!/usr/bin/env python3
"""
Seed product categories and ensure at least N%% of products have active inventory.

Usage (inside backend container):
  python scripts/seed_categories_and_inventory.py [--min-stock-ratio 0.6] [--dry-run]

Idempotency:
  - Categories: only fills when products.category IS NULL or empty
  - Inventory: only inserts one 'active' row per product that currently has none
"""
from __future__ import annotations

import argparse
import math
import os
import random
from datetime import date, timedelta
from typing import Optional, Tuple

import psycopg2
from psycopg2.extras import execute_batch


DEFAULT_DB_URL = "postgresql://postgres:postgres@postgres:5432/horticulture"


def db_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DB_URL)


def classify_category(name: str) -> Optional[str]:
    n = (name or "").strip().lower()
    if not n:
        return None
    fruits = [
        "apple", "banana", "orange", "mango", "avocado", "papaya",
        "pineapple", "grape", "strawberry", "lemon", "lime", "watermelon",
    ]
    vegetables = [
        "tomato", "potato", "onion", "carrot", "cabbage", "pepper",
        "spinach", "lettuce", "cucumber", "garlic", "ginger", "beet",
    ]
    dairy = ["milk", "yogurt", "butter", "cheese"]
    grains = ["rice", "wheat", "maize", "teff", "barley", "sorghum"]
    herbs = ["basil", "mint", "cilantro", "parsley"]

    if any(k in n for k in fruits):
        return "fruit"
    if any(k in n for k in vegetables):
        return "vegetable"
    if any(k in n for k in dairy):
        return "dairy"
    if any(k in n for k in grains):
        return "grain"
    if any(k in n for k in herbs):
        return "herb"
    if "egg" in n:
        return "eggs"
    return None  # leave unknowns as-is


def pick_expiry_days(category: Optional[str]) -> int:
    c = (category or "").lower()
    if c in {"vegetable", "herb"}:
        return 5
    if c in {"fruit"}:
        return 10
    if c in {"dairy", "eggs"}:
        return 7
    return 14


def estimate_price(cur, product_id: int) -> Optional[float]:
    # Prefer competitor average (last 30 days)
    cur.execute(
        """
        SELECT AVG(price) FROM competitor_pricing
        WHERE product_id=%s AND date >= CURRENT_DATE - INTERVAL '30 days'
        """,
        (product_id,),
    )
    row = cur.fetchone()
    if row and row[0]:
        return float(row[0])

    # Fallback to transaction average
    cur.execute(
        """
        SELECT AVG(price_per_unit) FROM transaction_history WHERE product_id=%s
        """,
        (product_id,),
    )
    row = cur.fetchone()
    if row and row[0]:
        return float(row[0])
    return None


def random_quantity(category: Optional[str]) -> float:
    c = (category or "").lower()
    if c == "vegetable":
        return round(random.uniform(50, 200), 2)
    if c == "fruit":
        return round(random.uniform(30, 120), 2)
    if c in {"dairy", "eggs"}:
        return round(random.uniform(20, 80), 2)
    return round(random.uniform(20, 150), 2)


def ensure_categories(conn) -> int:
    cur = conn.cursor()
    cur.execute("SELECT product_id, product_name, category FROM products ORDER BY product_name")
    updates = []
    for pid, name, category in cur.fetchall():
        if category and str(category).strip():
            continue
        cat = classify_category(name)
        if cat:
            updates.append((cat, pid))
    if not updates:
        cur.close()
        return 0
    execute_batch(cur, "UPDATE products SET category=%s WHERE product_id=%s", updates, page_size=100)
    conn.commit()
    cur.close()
    return len(updates)


def ensure_inventory(conn, min_ratio: float, dry_run: bool = False) -> Tuple[int, int, int]:
    cur = conn.cursor()
    # Totals
    cur.execute("SELECT COUNT(*) FROM products")
    total_products = int(cur.fetchone()[0])
    cur.execute("SELECT COUNT(DISTINCT product_id) FROM inventory WHERE status='active'")
    have_active = int(cur.fetchone()[0])

    target = math.ceil(total_products * min_ratio)
    to_add = max(0, target - have_active)

    if to_add <= 0:
        cur.close()
        return total_products, have_active, 0

    # Pick products without active inventory
    cur.execute(
        """
        SELECT p.product_id, p.product_name, p.category
        FROM products p
        WHERE NOT EXISTS (
            SELECT 1 FROM inventory i WHERE i.product_id = p.product_id AND i.status='active'
        )
        ORDER BY p.product_name
        LIMIT %s
        """,
        (to_add,),
    )
    rows = cur.fetchall()

    inserts = []
    today = date.today()
    for pid, name, category in rows:
        price = estimate_price(cur, pid)
        if price is None:
            # Reasonable default if no data available
            price = round(random.uniform(20, 150), 2)
        qty = random_quantity(category)
        expiry = today + timedelta(days=pick_expiry_days(category))
        inserts.append(
            (
                pid,  # product_id
                qty,
                price,
                today,
                expiry,
                None,  # image_url
                'active',
            )
        )

    if dry_run:
        cur.close()
        return total_products, have_active, len(inserts)

    execute_batch(
        cur,
        """
        INSERT INTO inventory (
            product_id, quantity_kg, price_per_unit, available_date, expiry_date, image_url, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        inserts,
        page_size=200,
    )
    conn.commit()
    cur.close()
    return total_products, have_active, len(inserts)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-stock-ratio", type=float, default=float(os.getenv("MIN_STOCK_RATIO", 0.6)))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = psycopg2.connect(db_url())
    try:
        updated = ensure_categories(conn)
        total, have_active, added = ensure_inventory(conn, args.min_stock_ratio, args.dry_run)
    finally:
        conn.close()

    print(f"Categories updated: {updated}")
    print(f"Products total: {total}")
    print(f"Products with active inventory (before): {have_active}")
    print(f"Inventory rows inserted: {added}{' (dry-run)' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

