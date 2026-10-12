import json

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="NovaMart Mock Backend")


with open("orders.json", "r") as file:
    ORDERS = json.load(file)


class OrderLookupRequest(BaseModel):
    order_id: str


@app.post("/api/lookup_order")
def lookup_order(request: OrderLookupRequest):
    order = ORDERS.get(request.order_id)

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
    return {
        "success": True,
        "order_id": request.order_id,
        "new_address": request.new_address,
        "updated_at": datetime.utcnow().isoformat() + "Z"
    }