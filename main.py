import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import get_order, init_db, insert_order, list_orders, next_order_id, update_order_address

app = FastAPI(title="NovaMart Mock Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


init_db()


class OrderLookupRequest(BaseModel):
    order_id: str


@app.post("/api/lookup_order")
def lookup_order(request: OrderLookupRequest):
    order = get_order(request.order_id)

    if not order:
        return {
            "status": "not_found",
            "order_id": request.order_id
        }

    return order

class VerifyIdentityRequest(BaseModel):
    account_number: str
    postcode: str


@app.post("/api/verify_identity")
def verify_identity(request: VerifyIdentityRequest):
    if request.account_number == "10000001" and request.postcode == "94107":
        return {
            "success": True,
            "customer_name": "Jordan Rivera",
            "account_number": "10000001"
        }

    if request.account_number == "10000002" and request.postcode == "10001":
        return {
            "success": True,
            "customer_name": "Sam Patel",
            "account_number": "10000002"
        }

    return {
        "success": False
    }

from datetime import datetime


class UpdateShippingAddressRequest(BaseModel):
    account_number: str
    order_id: str
    new_address: str


@app.post("/api/update_shipping_address")
def update_shipping_address(request: UpdateShippingAddressRequest):
    if not update_order_address(request.order_id, request.new_address):
        return {
            "success": False,
            "error": "order_not_found",
            "order_id": request.order_id
        }

    return {
        "success": True,
        "order_id": request.order_id,
        "new_address": request.new_address,
        "updated_at": datetime.utcnow().isoformat() + "Z"
    }


# Products catalog
PRODUCTS = [
    {"id": "p1", "name": "Nova Headphones X1", "price": 149.0, "image": "https://picsum.photos/id/1015/600/600", "description": "Wireless noise-canceling headphones", "category": "Audio"},
    {"id": "p2", "name": "Nova Smart Speaker Mini", "price": 79.0, "image": "https://picsum.photos/id/160/600/600", "description": "Compact smart speaker with voice control", "category": "Smart Home"},
    {"id": "p3", "name": "Nova Smart Plug", "price": 24.0, "image": "https://picsum.photos/id/201/600/600", "description": "WiFi-enabled smart plug", "category": "Smart Home"},
    {"id": "p4", "name": "Nova Earbuds Pro", "price": 129.0, "image": "https://picsum.photos/id/180/600/600", "description": "True wireless earbuds with ANC", "category": "Audio"},
    {"id": "p5", "name": "Nova Security Cam", "price": 99.0, "image": "https://picsum.photos/id/251/600/600", "description": "1080p indoor security camera", "category": "Security"},
    {"id": "p6", "name": "Nova Thermostat", "price": 199.0, "image": "https://picsum.photos/id/106/600/600", "description": "Smart learning thermostat", "category": "Smart Home"},
]


@app.get("/api/orders")
def get_orders():
    return list_orders()


@app.get("/api/products")
def get_products():
    return PRODUCTS


class CartItem(BaseModel):
    product_id: str
    quantity: int


class CreateOrderRequest(BaseModel):
    items: list[CartItem]
    customer_email: str
    shipping_address: str


@app.post("/api/create_order")
def create_order(request: CreateOrderRequest):
    order_id = next_order_id()

    # Calculate expected delivery (3 days from now)
    from datetime import timedelta
    expected_delivery = (datetime.utcnow() + timedelta(days=3)).strftime("%Y-%m-%d")
    
    # Build order items with prices
    order_items = []
    for cart_item in request.items:
        product = next((p for p in PRODUCTS if p["id"] == cart_item.product_id), None)
        if product:
            order_items.append({
                "name": product["name"],
                "price": product["price"],
                "qty": cart_item.quantity
            })
    
    # Create order object
    new_order = {
        "order_id": order_id,
        "expected_delivery_date": expected_delivery,
        "shipping_address": request.shipping_address,
        "fulfillment_center": "FC-WEST-03",
        "status": "processing",
        "items": order_items,
        "customer_email": request.customer_email
    }
    
    # Persist to SQLite
    insert_order(new_order)

    return {
        "success": True,
        "order_id": order_id,
        "order": new_order
    }