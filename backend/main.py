"""NovaMart backend API (FastAPI).

Serves two consumers from one app:

* The storefront (React + Vite): GET /api/products, GET /api/orders,
  POST /api/create_order.
* The ElevenLabs voice agent "Nova" (webhook tools): POST /api/lookup_order,
  POST /api/verify_identity, POST /api/update_shipping_address.

Security model for the privileged voice tool: ``update_shipping_address``
requires the caller's ``account_number`` to match the account that owns the
order. The previous implementation accepted ``account_number`` but never
checked it, so anyone could change anyone's address. Fixed here.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

import database

app = FastAPI(title="NovaMart Mock Backend API", version="1.0.0")

# The Vite dev server runs on :5173; allow it to reach the API on :8000.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Time helpers — datetime.utcnow() is deprecated since Python 3.12; use
# timezone-aware now() everywhere.
# ---------------------------------------------------------------------------

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Catalog — 8 SKUs across two categories (Audio, Home), per the lab scenario
# ---------------------------------------------------------------------------

PRODUCTS = [
    {"id": "p1", "name": "Nova Headphones X1", "price": 149.00,
     "image": "https://picsum.photos/id/1015/600/600",
     "description": "Wireless noise-canceling headphones, 40h battery",
     "category": "Audio"},
    {"id": "p2", "name": "Nova Smart Speaker Mini", "price": 79.00,
     "image": "https://picsum.photos/id/1080/600/600",
     "description": "Compact smart speaker with room-filling sound",
     "category": "Audio"},
    {"id": "p3", "name": "Nova Soundbar S2", "price": 229.00,
     "image": "https://picsum.photos/id/1084/600/600",
     "description": "2.1 channel soundbar with wireless subwoofer",
     "category": "Audio"},
    {"id": "p4", "name": "Nova Earbuds Air", "price": 89.00,
     "image": "https://picsum.photos/id/1062/600/600",
     "description": "True wireless earbuds with active noise cancellation",
     "category": "Audio"},
    {"id": "p5", "name": "Nova Smart Lamp", "price": 59.00,
     "image": "https://picsum.photos/id/1060/600/600",
     "description": "Dimmable smart lamp with 16M colors and schedules",
     "category": "Home"},
    {"id": "p6", "name": "Nova Air Purifier P3", "price": 199.00,
     "image": "https://picsum.photos/id/1068/600/600",
     "description": "HEPA air purifier for rooms up to 40 m²",
     "category": "Home"},
    {"id": "p7", "name": "Nova Robot Vacuum V5", "price": 349.00,
     "image": "https://picsum.photos/id/1074/600/600",
     "description": "LiDAR robot vacuum with self-empty dock",
     "category": "Home"},
    {"id": "p8", "name": "Nova Video Doorbell D1", "price": 129.00,
     "image": "https://picsum.photos/id/250/600/600",
     "description": "1080p video doorbell with two-way talk",
     "category": "Home"},
]

PRODUCT_INDEX = {p["id"]: p for p in PRODUCTS}

# Identity store for KBA verification (from the lab's test credentials).
# Anything not in this table fails verification, which drives the
# retry / lockout branches of the agent workflow.
IDENTITIES = {
    "10000001": {"postcode": "94107", "customer_name": "Jordan Rivera"},
    "10000002": {"postcode": "10001", "customer_name": "Sam Patel"},
}

FULFILLMENT_CENTERS = ["FC-WEST-03", "FC-EAST-01"]


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class OrderLookupRequest(BaseModel):
    order_id: str = Field(..., examples=["ORD-1001"])


class VerifyIdentityRequest(BaseModel):
    account_number: str = Field(..., examples=["10000001"])
    postcode: str = Field(..., examples=["94107"])


class UpdateShippingAddressRequest(BaseModel):
    account_number: str = Field(..., examples=["10000001"])
    order_id: str = Field(..., examples=["ORD-1001"])
    new_address: str = Field(..., min_length=5, examples=["123 Market Street, San Francisco, CA 94107"])


class CartItem(BaseModel):
    product_id: str
    quantity: int = Field(..., ge=1)


class CreateOrderRequest(BaseModel):
    items: list[CartItem] = Field(..., min_length=1)
    customer_email: EmailStr
    shipping_address: str = Field(..., min_length=5)
    # Optional: link the order to a store account so the voice agent can
    # authorize address changes against it later.
    account_number: Optional[str] = None


# ---------------------------------------------------------------------------
# Store API
# ---------------------------------------------------------------------------

@app.get("/api/products")
def get_products():
    return PRODUCTS


@app.get("/api/orders")
def get_orders():
    return database.list_orders()


@app.post("/api/create_order", status_code=200)
def create_order(payload: CreateOrderRequest):
    # Validate that every product exists. The old implementation silently
    # skipped unknown IDs, which meant customers paid for items that never
    # shipped and the agent couldn't explain the order contents. Now the
    # request is rejected up front with the offending IDs.
    unknown = [item.product_id for item in payload.items if item.product_id not in PRODUCT_INDEX]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unknown_product_ids",
                "unknown_product_ids": sorted(set(unknown)),
                "message": f"Unknown product id(s): {', '.join(sorted(set(unknown)))}",
            },
        )

    now = utcnow()
    order_items = []
    for item in payload.items:
        product = PRODUCT_INDEX[item.product_id]
        order_items.append({"name": product["name"], "price": product["price"], "qty": item.quantity})

    order = {
        "order_id": f"ORD-{database.next_order_number()}",
        "account_number": payload.account_number,
        "customer_email": payload.customer_email,
        "status": "processing",
        "items": order_items,
        "shipping_address": payload.shipping_address,
        # Delivery promise: 3 calendar days out from order placement.
        "expected_delivery_date": (now + timedelta(days=3)).date().isoformat(),
        "fulfillment_center": FULFILLMENT_CENTERS[now.toordinal() % len(FULFILLMENT_CENTERS)],
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    database.insert_order(order)
    return {"success": True, "order_id": order["order_id"], "order": order}


# ---------------------------------------------------------------------------
# Voice-agent API (ElevenLabs webhook tools)
# ---------------------------------------------------------------------------

@app.post("/api/lookup_order")
def lookup_order(payload: OrderLookupRequest):
    order = database.get_order(payload.order_id)
    if not order:
        # HTTP 200 with a semantic not_found body so the agent workflow can
        # branch on the tool result rather than on an error status.
        return {"status": "not_found", "order_id": payload.order_id}
    return order


@app.post("/api/verify_identity")
def verify_identity(payload: VerifyIdentityRequest):
    record = IDENTITIES.get(payload.account_number)
    if not record or record["postcode"] != payload.postcode:
        # 200 + success:false (not 4xx) so the workflow can branch on the
        # semantic result and count attempts toward lockout.
        return {"success": False}
    return {
        "success": True,
        "customer_name": record["customer_name"],
        "account_number": payload.account_number,
    }


@app.post("/api/update_shipping_address")
def update_shipping_address(payload: UpdateShippingAddressRequest):
    order = database.get_order(payload.order_id)
    if not order:
        return {"success": False, "error": "order_not_found", "order_id": payload.order_id}

    # SECURITY FIX: the account_number used to be accepted but never checked,
    # so any caller could redirect any order. Now the caller must prove they
    # own the account the order belongs to. Orders without an account number
    # (guest checkout) cannot be modified via the voice channel at all.
    if not order.get("account_number") or order["account_number"] != payload.account_number:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "message": "account_number does not own this order",
                "order_id": payload.order_id,
            },
        )

    updated_at = utcnow().isoformat()
    database.update_shipping_address(payload.order_id, payload.new_address, updated_at)
    return {
        "success": True,
        "order_id": payload.order_id,
        "new_address": payload.new_address,
        "updated_at": updated_at,
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "database": "turso" if database.USE_TURSO else "sqlite"}
