#!/usr/bin/env python3
"""
Dataset loader and knowledge base ingester for Milestone 2.

Responsibilities:
- Seed products from transactions dataset
- Load competitor pricing and transaction history in batches
- Ingest product knowledge base into Chroma (RAG)

The script is safe to re-run (UPSERT/ON CONFLICT where applicable).

Usage (inside container):
  python scripts/load_dataset.py
"""
import os
import sys
import math
import time
import logging
from typing import Dict, List, Tuple

import psycopg2
from psycopg2.extras import execute_batch
import pandas as pd


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

DEFAULT_DB_URL = "postgresql://postgres:postgres@postgres:5432/horticulture"


def db_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DB_URL)


def find_file(candidates: List[str]) -> str | None:
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return None


def get_dataset_paths() -> Tuple[str | None, str | None]:
    # Try common locations (mounted via docker-compose as /data)
    xlsx_candidates = [
        os.getenv("TXN_XLSX_PATH"),
        "/data/synthetic_horticulture_dataset.xlsx",
        os.path.join(os.getcwd(), "data", "synthetic_horticulture_dataset.xlsx"),
        os.path.abspath(os.path.join(os.getcwd(), "..", "data", "synthetic_horticulture_dataset.xlsx")),
    ]
    kb_candidates = [
        os.getenv("KB_CSV_PATH"),
        "/data/product_knowledge_base.csv",
        os.path.join(os.getcwd(), "data", "product_knowledge_base.csv"),
        os.path.abspath(os.path.join(os.getcwd(), "..", "data", "product_knowledge_base.csv")),
    ]
    return find_file(xlsx_candidates), find_file(kb_candidates)


def ensure_products(conn, transactions_df: pd.DataFrame) -> Dict[str, int]:
    cur = conn.cursor()
    # Extract unique products and guess unit/category if available
    products = (
        transactions_df[["product_name"]]
        .dropna()
        .drop_duplicates()
        .sort_values("product_name")
    )

    rows = []
    for name in products["product_name"].tolist():
        # Naive mapping; dataset can override later if columns exist
        category = None
        unit = "kg"  # default for horticulture; dairy might be liters
        if any(k in name.lower() for k in ["milk", "yogurt", "butter"]):
            unit = "liters"
        rows.append((name, category, unit))

    execute_batch(
        cur,
        """
        INSERT INTO products (product_name, category, unit)
        VALUES (%s, %s, %s)
        ON CONFLICT (product_name) DO NOTHING
        """,
        rows,
        page_size=100,
    )

    # Build mapping product_name -> product_id
    cur.execute("SELECT product_id, product_name FROM products;")
    mapping = {name: pid for pid, name in cur.fetchall()}
    conn.commit()
    cur.close()
    logging.info("Products ensured: %d unique", len(mapping))
    return mapping


def batch_insert_competitor_pricing(conn, df: pd.DataFrame, name_to_id: Dict[str, int]):
    required_cols = {"date", "product_name", "price", "source_market_type", "location_detail"}
    missing = required_cols - set(df.columns)
    if missing:
        logging.warning("Competitor_Pricing sheet missing columns: %s; skipping.", missing)
        return

    cur = conn.cursor()
    rows = []
    for _, r in df.iterrows():
        product_name = str(r["product_name"]).strip()
        pid = name_to_id.get(product_name)
        if not pid:
            continue
        rows.append(
            (
                pd.to_datetime(r["date"]).date(),
                pid,
                product_name,
                float(r["price"]),
                str(r["source_market_type"]).strip() if not pd.isna(r["source_market_type"]) else None,
                str(r["location_detail"]).strip() if not pd.isna(r["location_detail"]) else None,
            )
        )

    if not rows:
        logging.warning("No competitor pricing rows to insert.")
        cur.close()
        return

    execute_batch(
        cur,
        """
        INSERT INTO competitor_pricing (date, product_id, product_name, price, source_market_type, location_detail)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        rows,
        page_size=1000,
    )
    conn.commit()
    cur.close()
    logging.info("Inserted competitor pricing rows: %d", len(rows))


def batch_insert_transactions(conn, df: pd.DataFrame, name_to_id: Dict[str, int]):
    required_cols = {"order_date", "product_name", "quantity_ordered", "price_per_unit", "order_total_amount"}
    missing = required_cols - set(df.columns)
    if missing:
        logging.warning("Transactions sheet missing columns: %s; skipping.", missing)
        return

    cur = conn.cursor()
    rows = []
    for _, r in df.iterrows():
        product_name = str(r["product_name"]).strip()
        pid = name_to_id.get(product_name)
        if not pid:
            continue
        rows.append(
            (
                pd.to_datetime(r["order_date"]),
                pid,
                product_name,
                float(r["quantity_ordered"]),
                float(r["price_per_unit"]),
                float(r["order_total_amount"]),
            )
        )

    if not rows:
        logging.warning("No transaction rows to insert.")
        cur.close()
        return

    execute_batch(
        cur,
        """
        INSERT INTO transaction_history (
            order_date, product_id, product_name, quantity_ordered, price_per_unit, order_total_amount
        ) VALUES (%s, %s, %s, %s, %s, %s)
        """,
        rows,
        page_size=1000,
    )
    conn.commit()
    cur.close()
    logging.info("Inserted transaction rows: %d", len(rows))


def ingest_knowledge_base(csv_path: str):
    # Lazy import to keep DB-only runs fast
    try:
        from app.services.rag_service import VectorDBService
    except Exception as e:
        logging.error("Failed to import RAG service: %s", e)
        return

    try:
        service = VectorDBService()
        count = service.ingest_knowledge_base(csv_path)
        logging.info("Ingested knowledge base entries: %d", count)
    except Exception as e:
        logging.error("Knowledge base ingestion failed: %s", e)


def main():
    xlsx_path, kb_path = get_dataset_paths()
    if not xlsx_path:
        logging.warning(
            "Transactions workbook not found. Place it at /data/synthetic_horticulture_dataset.xlsx or set TXN_XLSX_PATH."
        )
    if not kb_path:
        logging.warning(
            "Knowledge base CSV not found. Place it at /data/product_knowledge_base.csv or set KB_CSV_PATH."
        )

    if not xlsx_path and not kb_path:
        logging.info("Nothing to load. Exiting.")
        return

    # Connect DB
    conn = psycopg2.connect(db_url())
    logging.info("Connected to DB.")

    if xlsx_path:
        logging.info("Reading workbook: %s", xlsx_path)
        # Load sheets if present
        xls = pd.ExcelFile(xlsx_path)
        sheet_names = set([s.lower() for s in xls.sheet_names])

        # Transactions sheet
        tx_df = None
        for cand in ["transactions", "Transactions"]:
            if cand in xls.sheet_names:
                tx_df = xls.parse(cand)
                break
        if tx_df is None:
            # Try case-insensitive match
            matches = [s for s in xls.sheet_names if s.lower() == "transactions"]
            if matches:
                tx_df = xls.parse(matches[0])

        # Competitor pricing sheet
        cp_df = None
        for cand in ["Competitor_Pricing", "competitor_pricing", "Competitor Pricing"]:
            if cand in xls.sheet_names:
                cp_df = xls.parse(cand)
                break
        if cp_df is None:
            matches = [s for s in xls.sheet_names if s.lower().replace(" ", "_") == "competitor_pricing"]
            if matches:
                cp_df = xls.parse(matches[0])

        # Ensure products
        if tx_df is not None and "product_name" in tx_df.columns:
            name_to_id = ensure_products(conn, tx_df)
        else:
            logging.warning("Transactions sheet not present or missing product_name; cannot seed products.")
            name_to_id = {}

        # Insert competitor pricing
        if cp_df is not None:
            batch_insert_competitor_pricing(conn, cp_df, name_to_id)
        else:
            logging.warning("Competitor_Pricing sheet not found; skipping.")

        # Insert transactions
        if tx_df is not None:
            batch_insert_transactions(conn, tx_df, name_to_id)
        else:
            logging.warning("Transactions sheet not found; skipping transactions load.")

    # Ingest knowledge base if present
    if kb_path:
        ingest_knowledge_base(kb_path)

    conn.close()
    logging.info("Dataset loading completed.")


if __name__ == "__main__":
    main()
