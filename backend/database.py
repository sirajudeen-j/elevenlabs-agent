"""Database layer for the NovaMart backend.

Two backends behind one interface:

* Local development: SQLite file on disk (stdlib ``sqlite3``, zero config).
* Deployed: Turso (libSQL over HTTP) when ``TURSO_DATABASE_URL`` and
  ``TURSO_AUTH_TOKEN`` are set.

The store API and the voice-agent API both use this module, so orders
created on the website are the same orders the ElevenLabs agent can look
up and update by voice.
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------

TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL", "").strip()
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "").strip()
SQLITE_PATH = os.environ.get("SQLITE_PATH", os.path.join(os.path.dirname(__file__), "novamart.db"))

USE_TURSO = bool(TURSO_DATABASE_URL and TURSO_AUTH_TOKEN)


# ---------------------------------------------------------------------------
# Turso (libSQL over HTTP) client — Hrana pipeline API, no extra deps needed
# beyond ``requests``. Endpoint: POST {url}/v2/pipeline
# ---------------------------------------------------------------------------

class _TursoClient:
    def __init__(self, url: str, token: str) -> None:
        import requests  # imported lazily so local dev doesn't need it

        self._requests = requests
        # Accept both libsql:// and https:// URLs; the HTTP API is https only.
        self._base = url.replace("libsql://", "https://").rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def execute(self, sql: str, args: Optional[list] = None) -> list[dict[str, Any]]:
        payload = {
            "requests": [
                {"type": "execute", "stmt": {"sql": sql, "args": [_encode(a) for a in (args or [])]}},
                {"type": "close"},
            ]
        }
        resp = self._requests.post(
            f"{self._base}/v2/pipeline", headers=self._headers, json=payload, timeout=15
        )
        resp.raise_for_status()
        body = resp.json()
        result = body["results"][0]
        if result["type"] != "ok":
            raise RuntimeError(f"Turso error: {result.get('error', {}).get('message', 'unknown')}")
        rs = result["response"]["result"]
        cols = [c["name"] for c in rs.get("cols", [])]
        rows = []
        for row in rs.get("rows", []):
            rows.append({col: _decode(cell) for col, cell in zip(cols, row)})
        return rows

    def executescript(self, statements: list[tuple[str, list]]) -> None:
        payload = {
            "requests": [
                {"type": "execute", "stmt": {"sql": sql, "args": [_encode(a) for a in args]}}
                for sql, args in statements
            ]
            + [{"type": "close"}]
        }
        resp = self._requests.post(
            f"{self._base}/v2/pipeline", headers=self._headers, json=payload, timeout=15
        )
        resp.raise_for_status()
        for result in resp.json()["results"][:-1]:
            if result["type"] != "ok":
                raise RuntimeError(f"Turso error: {result.get('error', {}).get('message', 'unknown')}")


def _encode(value: Any) -> dict[str, Any]:
    """Encode a Python value as a Hrana typed value."""
    if value is None:
        return {"type": "null", "value": None}
    if isinstance(value, bool):
        return {"type": "integer", "value": "1" if value else "0"}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        return {"type": "float", "value": value}
    return {"type": "text", "value": str(value)}


def _decode(cell: dict[str, Any]) -> Any:
    """Decode a Hrana typed value back to a Python value."""
    t = cell.get("type")
    v = cell.get("value")
    if t == "null" or v is None:
        return None
    if t == "integer":
        return int(v)
    if t == "float":
        return float(v)
    return v


# ---------------------------------------------------------------------------
# SQLite client (local development)
# ---------------------------------------------------------------------------

class _SqliteClient:
    def __init__(self, path: str) -> None:
        self._path = path
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")

    def execute(self, sql: str, args: Optional[list] = None) -> list[dict[str, Any]]:
        cur = self._conn.execute(sql, args or [])
        rows = [dict(r) for r in cur.fetchall()]
        self._conn.commit()
        return rows

    def executescript(self, statements: list[tuple[str, list]]) -> None:
        for sql, args in statements:
            self._conn.execute(sql, args)
        self._conn.commit()


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def _client():
    if USE_TURSO:
        return _TursoClient(TURSO_DATABASE_URL, TURSO_AUTH_TOKEN)
    return _SqliteClient(SQLITE_PATH)


_db = None


def get_db():
    """Lazily create the singleton client so tests can swap env vars."""
    global _db
    if _db is None:
        _db = _client()
        init_db()
    return _db


def reset_db() -> None:
    """Drop the singleton (used by tests to get a fresh database)."""
    global _db
    _db = None


SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    account_number TEXT,
    customer_email TEXT NOT NULL,
    status TEXT NOT NULL,
    items TEXT NOT NULL,               -- JSON array of {name, price, qty}
    shipping_address TEXT NOT NULL,
    expected_delivery_date TEXT NOT NULL,
    fulfillment_center TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

# Demo seed orders keyed to the two test accounts from the lab credentials:
#   10000001 / 94107 -> Jordan Rivera (happy path)
#   10000002 / 10001 -> Sam Patel     (cross-flow)
SEED_ORDERS = [
    {
        "order_id": "ORD-1001",
        "account_number": "10000001",
        "customer_email": "jordan.rivera@example.com",
        "status": "shipped",
        "items": [{"name": "Nova Headphones X1", "price": 149.00, "qty": 1}],
        "shipping_address": "742 Evergreen Terrace, Springfield",
        "expected_delivery_date": "2026-05-22",
        "fulfillment_center": "FC-WEST-03",
        "created_at": "2026-05-18T09:30:00+00:00",
        "updated_at": "2026-05-18T09:30:00+00:00",
    },
    {
        "order_id": "ORD-1002",
        "account_number": "10000002",
        "customer_email": "sam.patel@example.com",
        "status": "processing",
        "items": [{"name": "Nova Smart Speaker Mini", "price": 79.00, "qty": 2}],
        "shipping_address": "1600 Pennsylvania Ave NW, Washington DC",
        "expected_delivery_date": "2026-05-25",
        "fulfillment_center": "FC-EAST-01",
        "created_at": "2026-05-19T14:05:00+00:00",
        "updated_at": "2026-05-19T14:05:00+00:00",
    },
]

_INSERT_SQL = """
INSERT INTO orders (
    order_id, account_number, customer_email, status, items,
    shipping_address, expected_delivery_date, fulfillment_center,
    created_at, updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def init_db() -> None:
    db = get_db_raw()
    db.executescript([(SCHEMA, [])])
    # Idempotent seed: only insert orders that are not already present.
    for order in SEED_ORDERS:
        existing = db.execute("SELECT order_id FROM orders WHERE order_id = ?", [order["order_id"]])
        if not existing:
            _insert_order_row(order)


def get_db_raw():
    """Return the underlying client without triggering init (avoids recursion)."""
    global _db
    if _db is None:
        _db = _client()
    return _db


def _insert_order_row(order: dict) -> None:
    db = get_db_raw()
    db.executescript(
        [
            (
                _INSERT_SQL,
                [
                    order["order_id"],
                    order.get("account_number"),
                    order["customer_email"],
                    order["status"],
                    json.dumps(order["items"]),
                    order["shipping_address"],
                    order["expected_delivery_date"],
                    order["fulfillment_center"],
                    order["created_at"],
                    order["updated_at"],
                ],
            )
        ]
    )


def insert_order(order: dict) -> None:
    """Insert a new order (ensures schema exists first)."""
    get_db()
    _insert_order_row(order)


def get_order(order_id: str) -> Optional[dict]:
    rows = get_db().execute("SELECT * FROM orders WHERE order_id = ?", [order_id])
    return _row_to_order(rows[0]) if rows else None


def list_orders() -> list[dict]:
    rows = get_db().execute("SELECT * FROM orders ORDER BY created_at DESC")
    return [_row_to_order(r) for r in rows]


def update_shipping_address(order_id: str, new_address: str, updated_at: str) -> Optional[dict]:
    """Update the address and return the updated order, or None if missing."""
    db = get_db()
    db.executescript(
        [
            (
                "UPDATE orders SET shipping_address = ?, updated_at = ? WHERE order_id = ?",
                [new_address, updated_at, order_id],
            )
        ]
    )
    return get_order(order_id)


def next_order_number() -> int:
    """Next sequence number for generated order IDs (ORD-1003, ORD-1004, ...)."""
    rows = get_db().execute(
        "SELECT order_id FROM orders WHERE order_id LIKE 'ORD-%' ORDER BY order_id DESC LIMIT 1"
    )
    if not rows:
        return 1001
    try:
        return int(rows[0]["order_id"].split("-")[1]) + 1
    except (IndexError, ValueError):
        return 1001


def _row_to_order(row: dict) -> dict:
    order = dict(row)
    order["items"] = json.loads(order["items"])
    return order
