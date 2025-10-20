#!/usr/bin/env python3
"""
Database initialization script for Milestone 2.

Creates required PostgreSQL schema in an idempotent way.
Follows the schema and indexes defined in implementation_plan.md.

Usage (inside container):
  python scripts/init_db.py
"""
import os
import sys
import time
import logging
import psycopg2
from psycopg2.extras import execute_batch


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def get_db_url() -> str:
    # Default matches .env.example and docker-compose service names
    return os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@postgres:5432/horticulture",
    )


def wait_for_db(conn_str: str, retries: int = 20, delay: float = 2.0) -> None:
    for attempt in range(1, retries + 1):
        try:
            with psycopg2.connect(conn_str):
                logging.info("Connected to PostgreSQL.")
                return
        except Exception as e:
            logging.info("Waiting for PostgreSQL to be ready (%d/%d): %s", attempt, retries, e)
            time.sleep(delay)
    raise RuntimeError("PostgreSQL is not ready after retries.")


def create_schema(conn):
    cur = conn.cursor()

    # Enable UUID extension
    cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # Users table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            phone VARCHAR(15) UNIQUE NOT NULL,
            name VARCHAR(100),
            user_type VARCHAR(20) NOT NULL DEFAULT 'customer' CHECK (user_type IN ('customer','supplier')),
            default_location VARCHAR(100),
            created_at TIMESTAMP DEFAULT NOW()
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);")

    # Products table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            product_id SERIAL PRIMARY KEY,
            product_name VARCHAR(100) NOT NULL UNIQUE,
            category VARCHAR(50),
            unit VARCHAR(20)
        );
        """
    )

    # Inventory table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory (
            inventory_id SERIAL PRIMARY KEY,
            supplier_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
            product_id INT REFERENCES products(product_id),
            quantity_kg DECIMAL(10,2) NOT NULL,
            price_per_unit DECIMAL(10,2) NOT NULL,
            available_date DATE NOT NULL,
            expiry_date DATE,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','sold_out','expired'))
        );
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_inventory_supplier_product_status
        ON inventory (supplier_id, product_id, status);
        """
    )

    # Orders table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            order_id UUID PRIMARY KEY,
            customer_id UUID REFERENCES users(user_id),
            supplier_id UUID REFERENCES users(user_id),
            order_date TIMESTAMP DEFAULT NOW(),
            delivery_date DATE NOT NULL,
            delivery_location VARCHAR(200) NOT NULL,
            total_amount DECIMAL(10,2) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','confirmed','delivered','cancelled')),
            payment_method VARCHAR(20) NOT NULL DEFAULT 'COD',
            created_at TIMESTAMP DEFAULT NOW()
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);")

    # Order items
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS order_items (
            item_id SERIAL PRIMARY KEY,
            order_id UUID REFERENCES orders(order_id) ON DELETE CASCADE,
            product_id INT REFERENCES products(product_id),
            quantity_kg DECIMAL(10,2) NOT NULL,
            price_per_unit DECIMAL(10,2) NOT NULL,
            subtotal DECIMAL(10,2) GENERATED ALWAYS AS (quantity_kg * price_per_unit) STORED
        );
        """
    )

    # Competitor pricing
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS competitor_pricing (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            product_id INT REFERENCES products(product_id),
            product_name VARCHAR(100),
            price DECIMAL(10,2) NOT NULL,
            source_market_type VARCHAR(50),
            location_detail VARCHAR(100)
        );
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_competitor_pricing_product_date_market
        ON competitor_pricing (product_id, date, source_market_type);
        """
    )

    # Transaction history
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS transaction_history (
            transaction_id SERIAL PRIMARY KEY,
            order_date TIMESTAMP NOT NULL,
            product_id INT REFERENCES products(product_id),
            product_name VARCHAR(100),
            quantity_ordered DECIMAL(10,2),
            price_per_unit DECIMAL(10,2),
            order_total_amount DECIMAL(10,2)
        );
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_transaction_history_product_date
        ON transaction_history (product_id, order_date);
        """
    )

    conn.commit()
    cur.close()


def main():
    db_url = get_db_url()
    logging.info("Using DATABASE_URL=%s", db_url)
    wait_for_db(db_url)

    with psycopg2.connect(db_url) as conn:
        logging.info("Creating schema (idempotent)...")
        create_schema(conn)
        logging.info("Database schema initialized successfully.")


if __name__ == "__main__":
    main()
