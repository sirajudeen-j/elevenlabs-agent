import json
import os
import sqlite3

DB_PATH = "novamart.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            expected_delivery_date TEXT,
            shipping_address TEXT,
            fulfillment_center TEXT,
            customer_email TEXT,
            items TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()

    # Seed from orders.json if the table is empty
    count = conn.execute("SELECT COUNT(*) AS c FROM orders").fetchone()["c"]
    if count == 0 and os.path.exists("orders.json"):
        with open("orders.json", "r") as f:
            seed = json.load(f)
        for order_id, order in seed.items():
            conn.execute(
                """
                INSERT OR IGNORE INTO orders
                (order_id, status, expected_delivery_date, shipping_address,
                 fulfillment_center, customer_email, items)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    order.get("status"),
                    order.get("expected_delivery_date"),
                    order.get("shipping_address"),
                    order.get("fulfillment_center"),
                    order.get("customer_email"),
                    json.dumps(order.get("items", [])),
                ),
            )
        conn.commit()

    conn.close()


def row_to_order(row):
    if not row:
        return None
    return {
        "order_id": row["order_id"],
        "status": row["status"],
        "expected_delivery_date": row["expected_delivery_date"],
        "shipping_address": row["shipping_address"],
        "fulfillment_center": row["fulfillment_center"],
        "customer_email": row["customer_email"],
        "items": json.loads(row["items"]),
        "created_at": row["created_at"],
    }


def get_order(order_id: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM orders WHERE order_id = ?", (order_id,)
    ).fetchone()
    conn.close()
    return row_to_order(row)


def next_order_id() -> str:
    conn = get_connection()
    row = conn.execute(
        "SELECT MAX(CAST(order_id AS INTEGER)) AS m FROM orders"
    ).fetchone()
    conn.close()
    return str((row["m"] or 10000) + 1)


def insert_order(order: dict):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO orders
        (order_id, status, expected_delivery_date, shipping_address,
         fulfillment_center, customer_email, items)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            order["order_id"],
            order["status"],
            order["expected_delivery_date"],
            order["shipping_address"],
            order["fulfillment_center"],
            order.get("customer_email"),
            json.dumps(order["items"]),
        ),
    )
    conn.commit()
    conn.close()
