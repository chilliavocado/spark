# api.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
from app.src.spark.data.loader import (
    load_product,
    load_products,
    load_customer,
    load_customers,
    save_interaction,
    add_customer,
    get_recommendations,
    get_next_interaction_id,
)
from app.src.spark.data.models import InteractionType
from stable_baselines3 import DQN
import torch
import numpy as np
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()


@router.get("/api/user")
async def get_user(user_id: int):
    """Fetch user profile and interaction history."""
    customer = load_customer(user_id)  # Load customer on demand
    if not customer:
        return JSONResponse(content={"error": "User not found"}, status_code=404)

    user_data = {
        "id": int(customer.idx),
        "zip_code": customer.zip_code,
        "city": customer.city,
        "state": customer.state,
        "num_views": sum(customer.views) if hasattr(customer, "views") else 0,
        "num_likes": sum(customer.likes) if hasattr(customer, "likes") else 0,
        "num_purchases": sum(customer.buys) if hasattr(customer, "buys") else 0,
        "num_ratings": sum(1 for r in customer.ratings if r > 0) if hasattr(customer, "ratings") else 0,
    }
    return JSONResponse(content=user_data)


@router.get("/api/product")
async def get_product(product_id: int):
    """Fetch a specific product by its ID."""
    product = load_product(product_id)  # Load product on demand
    if product:
        product_data = {
            "id": int(product.idx),
            "name": product.name,
            "price": f"{product.price:.2f}",
            "desc": product.desc,
            "long_desc": product.long_desc,
            "image": "product_image.png",
            "category": product.category if product.category else None,
        }
        return JSONResponse(content=product_data)
    else:
        return JSONResponse(content={"error": "Product not found"}, status_code=404)


@router.get("/api/products")
async def get_products():
    """Fetch all products available in the catalog."""
    products, _, _ = load_products()  # Load products on demand

    product_data = [{"id": p.idx, "name": p.name, "price": f"{p.price:.2f}", "desc": p.desc, "image": "product_image.png"} for p in products]
    return JSONResponse(content=product_data)


@router.get("/api/catalogue")
async def get_catalogue(category_id: Optional[int] = None):
    """Fetch products by category if category_id is specified, otherwise all products."""
    products, _, _ = load_products()  # Load products on demand

    filtered_products = [p for p in products if p.category.idx == category_id] if category_id else products
    catalogue_data = [{"id": p.idx, "name": p.name, "price": f"{p.price:.2f}", "desc": p.desc, "image": "product_image.png"} for p in filtered_products]
    return JSONResponse(content=catalogue_data)


class InteractionData(BaseModel):
    user_id: int
    product_id: int
    interaction_type: str
    value: Optional[float] = 0.0
    review_score: Optional[int] = None
    zip_code: Optional[int] = None
    city: Optional[str] = None
    state: Optional[str] = None


@router.post("/api/interaction")
async def push_interaction(interaction: InteractionData):
    """Save a new interaction and append it to the UserInteractionLog.csv file."""

    # Validate and map interaction type
    try:
        interaction_type_enum = InteractionType(interaction.interaction_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid interaction type")

    # Unpack interaction fields
    user_id = interaction.user_id
    product_id = interaction.product_id
    review_score = interaction.review_score if interaction.review_score is not None else 0
    zip_code = interaction.zip_code
    city = interaction.city
    state = interaction.state

    # Retrieve product price for the value field
    product = load_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if interaction_type_enum in [InteractionType.RATE, InteractionType.LIKE, InteractionType.VIEW]:
        value = 1
    else:
        value = product.price

    # Load or add the customer
    customer = load_customer(user_id)
    if not customer:
        if not all([zip_code, city, state]):
            raise HTTPException(status_code=400, detail="New customer requires zip_code, city, and state")

        # If new customer, add and load customers and indices
        customers, customer_id_to_index = load_customers()
        customer_idx = add_customer(
            user_id=user_id,
            zip_code=zip_code,
            city=city,
            state=state,
            customers=customers,
            customer_id_to_index=customer_id_to_index,
        )
    else:
        # Load customer indices if existing
        customers, customer_id_to_index = load_customers()
        customer_idx = customer_id_to_index[user_id]

    # Generate the next sequential interaction ID
    interaction_id = get_next_interaction_id()
    timestamp = datetime.now()

    # Prepare interaction data
    interaction_data = {
        "id": interaction_id,
        "timestamp": timestamp,
        "idx": f"order-{interaction_id}" if interaction_type_enum == InteractionType.BUY else f"review-{interaction_id}",
        "product_idx": product_id,
        "customer_idx": customer_idx,
        "review_score": review_score,
        "type": interaction_type_enum.value,
        "value": value,
    }

    # Append interaction to the separate log file
    save_interaction(interaction_data)

    return JSONResponse(content={"message": "Interaction saved successfully"})


@router.get("/api/recommendations")
async def fetch_recommendations(user_id: int):
    """Generate product recommendations for a specific user."""
    # Generate recommendations for the user
    recommendations_list = get_recommendations(user_id)
    if recommendations_list is None:
        return JSONResponse(content={"error": "User not found"}, status_code=404)

    return JSONResponse(content=recommendations_list)
