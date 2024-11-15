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
    get_recommendations,
    set_current_user,
    get_current_user,
    get_next_interaction_id,
)
from app.src.spark.data.models import InteractionType
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()


@router.get("/api/currentUser")
async def fetch_current_user():
    """Fetch the current user from the client-side or server-side variable."""
    user_id = get_current_user()
    return JSONResponse(content={"user_id": user_id})


@router.post("/api/setCurrentUser")
async def set_current_user_endpoint(user_id: int):
    """Set the current user ID in the server-side variable."""
    set_current_user(user_id)
    return JSONResponse(content={"message": f"User ID {user_id} set successfully"})


@router.get("/api/user")
async def get_user(user_id: int):
    """Fetch user profile and interaction history."""
    customer = load_customer(user_id)
    if not customer:
        return JSONResponse(content={"error": "User not found"}, status_code=404)

    user_data = {
        "id": int(customer.idx),
        "zip_code": customer.zip_code,
        "city": customer.city,
        "state": customer.state,
        "interactions": [
            {
                "id": interaction.idx,
                "timestamp": interaction.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "product_id": int(interaction.product_idx),
                "type": interaction.type.value,
                "value": f"{interaction.value:.2f}" if interaction.value is not None else "N/A",
                "review_score": interaction.review_score if interaction.review_score is not None else "N/A",
            }
            for interaction in customer.interactions
        ],
    }
    return JSONResponse(content=user_data)


@router.get("/api/users")
async def get_users():
    """Fetch all users and their interaction history."""
    customers = load_customers()
    user_data = [
        {
            "id": int(customer.idx),
            "zip_code": customer.zip_code,
            "city": customer.city,
            "state": customer.state,
            "interactions": [
                {
                    "id": interaction.idx,
                    "timestamp": interaction.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "product_id": int(interaction.product_idx),
                    "type": interaction.type.value,
                    "value": f"{interaction.value:.2f}" if interaction.value is not None else "N/A",
                    "review_score": interaction.review_score if interaction.review_score is not None else "N/A",
                }
                for interaction in customer.interactions
            ],
        }
        for customer in customers
    ]
    return JSONResponse(content=user_data)


@router.get("/api/product")
async def get_product(product_id: int):
    """Fetch a specific product by its ID."""
    product = load_product(product_id)
    if product:
        product_data = {
            "id": int(product.idx),
            "name": product.name,
            "price": f"{product.price:.2f}",
            "desc": product.desc,
            "long_desc": product.long_desc,
            "image": "product_image.png",
            "category": {"id": product.category.idx, "name": product.category.name, "desc": product.category.desc} if product.category else None,
        }
        return JSONResponse(content=product_data)
    else:
        return JSONResponse(content={"error": "Product not found"}, status_code=404)


@router.get("/api/products")
async def get_products():
    """Fetch all products available in the catalog."""
    products = load_products()
    product_data = [
        {
            "id": p.idx,
            "name": p.name,
            "price": f"{p.price:.2f}",
            "desc": p.desc,
            "image": f"{p.category.name}.jpeg" if p.category else "product_image.png",
            "category": {"id": p.category.idx, "name": p.category.name, "desc": p.category.desc} if p.category else None,
        }
        for p in products
    ]
    return JSONResponse(content=product_data)


@router.get("/api/catalogue")
async def get_catalogue(category_id: Optional[int] = None):
    """Fetch products by category if category_id is specified, otherwise all products."""
    products = load_products()

    # Filter products based on the category_id if provided
    filtered_products = [p for p in products if p.category and p.category.idx == category_id] if category_id else products

    catalogue_data = [
        {
            "cat_id": p.category.idx if p.category else None,
            "id": p.idx,
            "name": p.name,
            "price": f"{p.price:.2f}",
            "desc": p.desc,
            "image": f"{p.category.name}.jpeg" if p.category else "default.jpeg",
        }
        for p in filtered_products
    ]

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
    """Save a new interaction to user.json."""
    try:
        interaction_type_enum = InteractionType(interaction.interaction_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid interaction type")

    user_id = interaction.user_id
    product_id = interaction.product_id
    review_score = interaction.review_score if interaction.review_score is not None else 0

    product = load_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    value = 1 if interaction_type_enum in [InteractionType.RATE, InteractionType.LIKE, InteractionType.VIEW] else product.price

    interaction_id = get_next_interaction_id()
    timestamp = datetime.now()

    interaction_data = {
        "id": interaction_id,
        "timestamp": timestamp,
        "idx": f"order-{interaction_id}" if interaction_type_enum == InteractionType.BUY else f"review-{interaction_id}",
        "product_idx": product_id,
        "customer_idx": user_id,
        "review_score": review_score,
        "type": interaction_type_enum.value,
        "value": value,
    }

    save_interaction(interaction_data)
    return JSONResponse(content={"message": "Interaction saved successfully"})


@router.get("/api/recommendations")
async def fetch_recommendations(user_id: int):
    """Generate product recommendations for a specific user."""
    try:
        recommendations_list = get_recommendations(user_id)
        if recommendations_list is None:
            return JSONResponse(content={"error": "No recommendations available"}, status_code=404)
        return JSONResponse(content=recommendations_list)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
