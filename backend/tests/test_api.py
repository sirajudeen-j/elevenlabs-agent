"""API tests for the NovaMart backend.

Covers both the store API and the voice-agent webhook tools, including the
regressions called out in the action items:

* unknown product IDs must be rejected (they used to be silently skipped)
* address changes must be authorized by order ownership
* no deprecated datetime.utcnow() in the codebase
"""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import database
from main import app, PRODUCTS


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Fresh app + isolated SQLite database per test."""
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(database, "SQLITE_PATH", str(db_file))
    monkeypatch.setattr(database, "USE_TURSO", False)
    database.reset_db()
    with TestClient(app) as c:
        yield c
    database.reset_db()


# ---------------------------------------------------------------------------
# Store API
# ---------------------------------------------------------------------------

def test_list_products(client):
    resp = client.get("/api/products")
    assert resp.status_code == 200
    products = resp.json()
    assert len(products) == len(PRODUCTS) >= 8
    for p in products:
        assert {"id", "name", "price", "image", "description", "category"} <= p.keys()


def test_create_order_happy_path(client):
    resp = client.post("/api/create_order", json={
        "items": [{"product_id": "p1", "quantity": 1}, {"product_id": "p5", "quantity": 2}],
        "customer_email": "customer@example.com",
        "shipping_address": "123 Market Street, San Francisco, CA 94107",
        "account_number": "10000001",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["order_id"].startswith("ORD-")

    order = body["order"]
    assert order["status"] == "processing"
    expected_delivery = date.today() + timedelta(days=3)
    assert order["expected_delivery_date"] == expected_delivery.isoformat()
    assert order["items"] == [
        {"name": "Nova Headphones X1", "price": 149.0, "qty": 1},
        {"name": "Nova Smart Lamp", "price": 59.0, "qty": 2},
    ]
    # created_at must be a timezone-aware ISO timestamp
    created = datetime.fromisoformat(order["created_at"])
    assert created.tzinfo is not None


def test_create_order_rejects_unknown_product_ids(client):
    resp = client.post("/api/create_order", json={
        "items": [{"product_id": "p1", "quantity": 1}, {"product_id": "nope", "quantity": 1}],
        "customer_email": "customer@example.com",
        "shipping_address": "123 Market Street, San Francisco, CA 94107",
    })
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["error"] == "unknown_product_ids"
    assert detail["unknown_product_ids"] == ["nope"]


def test_create_order_validates_input(client):
    # empty items list
    resp = client.post("/api/create_order", json={
        "items": [],
        "customer_email": "customer@example.com",
        "shipping_address": "123 Market Street, San Francisco, CA 94107",
    })
    assert resp.status_code == 422
    # bad email
    resp = client.post("/api/create_order", json={
        "items": [{"product_id": "p1", "quantity": 1}],
        "customer_email": "not-an-email",
        "shipping_address": "123 Market Street, San Francisco, CA 94107",
    })
    assert resp.status_code == 422
    # zero quantity
    resp = client.post("/api/create_order", json={
        "items": [{"product_id": "p1", "quantity": 0}],
        "customer_email": "customer@example.com",
        "shipping_address": "123 Market Street, San Francisco, CA 94107",
    })
    assert resp.status_code == 422


def test_list_orders_contains_created_order(client):
    resp = client.post("/api/create_order", json={
        "items": [{"product_id": "p2", "quantity": 1}],
        "customer_email": "customer@example.com",
        "shipping_address": "1600 Pennsylvania Ave NW, Washington DC",
    })
    order_id = resp.json()["order_id"]
    orders = client.get("/api/orders").json()
    assert any(o["order_id"] == order_id for o in orders)
    # seed orders are present too
    assert any(o["order_id"] == "ORD-1001" for o in orders)


def test_order_ids_are_sequential(client):
    first = client.post("/api/create_order", json={
        "items": [{"product_id": "p1", "quantity": 1}],
        "customer_email": "a@example.com",
        "shipping_address": "1 First Street, Springfield",
    }).json()["order_id"]
    second = client.post("/api/create_order", json={
        "items": [{"product_id": "p1", "quantity": 1}],
        "customer_email": "b@example.com",
        "shipping_address": "2 Second Street, Springfield",
    }).json()["order_id"]
    assert first == "ORD-1003"   # seeds occupy ORD-1001 / ORD-1002
    assert second == "ORD-1004"


# ---------------------------------------------------------------------------
# Voice-agent tools
# ---------------------------------------------------------------------------

def test_lookup_order_found(client):
    resp = client.post("/api/lookup_order", json={"order_id": "ORD-1001"})
    assert resp.status_code == 200
    order = resp.json()
    assert order["order_id"] == "ORD-1001"
    assert order["status"] == "shipped"
    assert order["items"][0]["name"] == "Nova Headphones X1"
    assert order["fulfillment_center"] == "FC-WEST-03"


def test_lookup_order_not_found(client):
    resp = client.post("/api/lookup_order", json={"order_id": "ORD-9999"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "not_found", "order_id": "ORD-9999"}


def test_verify_identity_success(client):
    resp = client.post("/api/verify_identity",
                       json={"account_number": "10000001", "postcode": "94107"})
    assert resp.status_code == 200
    assert resp.json() == {
        "success": True, "customer_name": "Jordan Rivera", "account_number": "10000001",
    }


def test_verify_identity_rejected(client):
    # wrong postcode
    resp = client.post("/api/verify_identity",
                       json={"account_number": "10000001", "postcode": "00000"})
    assert resp.status_code == 200
    assert resp.json() == {"success": False}
    # unknown account
    resp = client.post("/api/verify_identity",
                       json={"account_number": "99999999", "postcode": "94107"})
    assert resp.status_code == 200
    assert resp.json() == {"success": False}


def test_update_shipping_address_happy_path(client):
    resp = client.post("/api/update_shipping_address", json={
        "account_number": "10000001",
        "order_id": "ORD-1001",
        "new_address": "500 New Avenue, San Francisco, CA 94107",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["new_address"] == "500 New Avenue, San Francisco, CA 94107"
    assert datetime.fromisoformat(body["updated_at"]).tzinfo is not None
    # persisted
    order = client.post("/api/lookup_order", json={"order_id": "ORD-1001"}).json()
    assert order["shipping_address"] == "500 New Avenue, San Francisco, CA 94107"


def test_update_shipping_address_order_not_found(client):
    resp = client.post("/api/update_shipping_address", json={
        "account_number": "10000001",
        "order_id": "ORD-9999",
        "new_address": "500 New Avenue, San Francisco, CA 94107",
    })
    assert resp.status_code == 200
    assert resp.json() == {
        "success": False, "error": "order_not_found", "order_id": "ORD-9999",
    }


def test_update_shipping_address_rejects_non_owner(client):
    """SECURITY: account_number must own the order (this used to go unchecked)."""
    resp = client.post("/api/update_shipping_address", json={
        "account_number": "10000002",          # Sam Patel trying to move Jordan Rivera's order
        "order_id": "ORD-1001",
        "new_address": "1 Attacker Lane, Nowhere",
    })
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "forbidden"
    # and the address must be unchanged
    order = client.post("/api/lookup_order", json={"order_id": "ORD-1001"}).json()
    assert order["shipping_address"] == "742 Evergreen Terrace, Springfield"


def test_update_shipping_address_guest_order_not_modifiable_by_voice(client):
    """Orders without an account_number (guest checkout) can't be changed by voice."""
    order_id = client.post("/api/create_order", json={
        "items": [{"product_id": "p1", "quantity": 1}],
        "customer_email": "guest@example.com",
        "shipping_address": "9 Guest Road, Springfield",
    }).json()["order_id"]
    resp = client.post("/api/update_shipping_address", json={
        "account_number": "10000001",
        "order_id": order_id,
        "new_address": "500 New Avenue, San Francisco, CA 94107",
    })
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Code hygiene
# ---------------------------------------------------------------------------

def test_no_deprecated_datetime_utcnow():
    """datetime.utcnow() is deprecated; the codebase must use aware now().

    AST-based so docstrings/comments mentioning the deprecation don't
    produce false positives — only real call sites are flagged.
    """
    import ast

    backend = Path(__file__).resolve().parent.parent
    offenders = []
    for py in backend.rglob("*.py"):
        tree = ast.parse(py.read_text())
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "utcnow"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "datetime"
            ):
                offenders.append(f"{py.name}:{node.lineno}")
    assert offenders == [], f"deprecated datetime.utcnow() call at: {offenders}"
