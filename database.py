import json
import os

TURSO_URL = os.environ.get("TURSO_DATABASE_URL")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")

# Local file DB. On Vercel (read-only FS) fall back to /tmp (ephemeral).
if os.environ.get("VERCEL"):
    DB_PATH = "/tmp/novamart.db"
else:
    DB_PATH = os.environ.get("SQLITE_PATH", "novamart.db")

_client = None


def _get_turso_client():
    global _client
    if _client is None:
        import libsql_client

        _client = libsql_client.create_client_sync(TURSO_URL, auth_token=TURSO_TOKEN)
    return _client


def _execute(sql, params=()):
    """Run a query and return rows as a list of dicts."""
    if TURSO_URL:
        result = _get_turso_client().execute(sql, list(params))
        cols = list(result.columns)
        return [dict(zip(cols, row)) for row in result.rows]

    import sqlite3

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        conn.commit()
        return rows
    finally:
        conn.close()


def init_db():
    _execute(
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

    # Seed from orders.json if the table is empty
    count = _execute("SELECT COUNT(*) AS c FROM orders")[0]["c"]
    if count == 0 and os.path.exists("orders.json"):
        with open("orders.json", "r") as f:
            seed = json.load(f)
        for order_id, order in seed.items():
            _execute(
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


def get_order(order_id: str):
    rows = _execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    if not rows:
        return None
    row = rows[0]
    row["items"] = json.loads(row["items"])
    return row


def next_order_id() -> str:
    row = _execute("SELECT MAX(CAST(order_id AS INTEGER)) AS m FROM orders")[0]
    return str((row["m"] or 10000) + 1)


def insert_order(order: dict):
    _execute(
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


def list_orders():
    rows = _execute("SELECT * FROM orders ORDER BY created_at DESC, order_id DESC")
    for row in rows:
        row["items"] = json.loads(row["items"])
    return rows


def update_order_address(order_id: str, new_address: str) -> bool:
    """Update the shipping address. Returns False if the order doesn't exist."""
    if get_order(order_id) is None:
        return False
    _execute(
        "UPDATE orders SET shipping_address = ? WHERE order_id = ?",
        (new_address, order_id),
    )
    return True
