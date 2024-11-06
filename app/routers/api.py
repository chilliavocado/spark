# api.py

from fastapi import APIRouter
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
    assign_interactions_to_customers,
)
from app.src.spark.data.models import InteractionType
from app.src.spark.agent.environment_v2 import UserBehaviorModel, RecommendationEnv
from stable_baselines3 import DQN
import torch
import numpy as np
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()


# Define the InteractionData model
class InteractionData(BaseModel):
    user_id: int
    product_id: int
    interaction_type: str
    value: Optional[float] = None
    review_score: Optional[int] = None
    zip_code: Optional[int] = None
    city: Optional[str] = None
    state: Optional[str] = None


# Helper function to load model and initialize environment
def initialize_env_and_model():
    model_path = "app/src/spark/agent/models/dqn_recommender"
    model = DQN.load(model_path)

    # Load products and customers
    products, max_price, product_id_to_index = load_products()
    num_products = len(products)
    customers, customer_id_to_index = load_customers(num_products)

    # Initialize environment
    user_behavior_model = UserBehaviorModel(customers=customers, num_products=num_products)
    env = RecommendationEnv(users=customers, products=products, top_k=5, max_price=max_price, user_behavior_model=user_behavior_model)

    return model, env, products, customers, customer_id_to_index


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
        "num_views": sum(customer.views),
        "num_likes": sum(customer.likes),
        "num_purchases": sum(customer.purchases),
        "num_ratings": sum(1 for r in customer.ratings if r > 0),
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
async def get_Products():
    """Fetch all products available in the catalog."""
    products, _, _ = load_products()  # Load products on demand

    product_data = [{"id": p.idx, "name": p.name, "price": f"{p.price:.2f}", "desc": p.desc, "image": "product_image.png"} for p in products]
    return JSONResponse(content=product_data)


@router.get("/api/recommendations")
async def get_Recommendations(user_id: int):
    """Generate top 5 product recommendations for a specific user after a major interaction."""
    model, env, products, customers, customer_id_to_index = initialize_env_and_model()

    # Generate recommendations for the user
    recommendations_list = get_recommendations(user_id, customers, customer_id_to_index, products, model, env, top_k=5)
    if recommendations_list is None:
        return JSONResponse(content={"error": "User not found"}, status_code=404)
    return JSONResponse(content=recommendations_list)


@router.get("/api/catalogue")
async def get_Catalogue(category_id: Optional[int] = None):
    """Fetch products by category if category_id is specified, otherwise all products."""
    products, _, _ = load_products()  # Load products on demand

    filtered_products = [p for p in products if p.category.idx == category_id] if category_id else products
    catalogue_data = [{"id": p.idx, "name": p.name, "price": f"{p.price:.2f}", "desc": p.desc, "image": "product_image.png"} for p in filtered_products]
    return JSONResponse(content=catalogue_data)


@router.post("/api/interaction")
async def save_Interaction(interaction: InteractionData):
    """Save a new interaction, adding a new user if needed."""
    try:
        interaction_type_enum = InteractionType(interaction.interaction_type)
    except ValueError:
        return JSONResponse(content={"error": "Invalid interaction type"}, status_code=400)

    user_id = interaction.user_id
    product_id = interaction.product_id
    value = interaction.value
    review_score = interaction.review_score
    zip_code = interaction.zip_code
    city = interaction.city
    state = interaction.state

    # Load customer data dynamically
    customers, customer_id_to_index = load_customers(num_products=0)
    customer_idx = customer_id_to_index.get(user_id)

    if customer_idx is None:
        if zip_code is None or city is None or state is None:
            return JSONResponse(
                content={"error": "New customer requires zip_code, city, and state"},
                status_code=400,
            )
        customer_idx = add_customer(user_id, zip_code, city, state, customers, customer_id_to_index, num_products=0)

    # Record interaction
    interaction_id = len(customers[customer_idx].interactions)
    timestamp = datetime.now()
    interaction_data = {
        "id": interaction_id,
        "timestamp": timestamp,
        "product_idx": product_id,
        "customer_idx": customer_idx,
        "type": interaction_type_enum,
        "value": value if value is not None else 0.0,
        "review_score": review_score,
    }

    save_interaction(interaction_data)
    assign_interactions_to_customers(customers, [interaction_data])

    return JSONResponse(content={"message": "Interaction saved successfully"})
