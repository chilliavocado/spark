from fastapi import APIRouter
from fastapi.responses import JSONResponse
from typing import Optional
from app.src.spark.data.loader import load_products, load_customers, save_interaction, add_customer, assign_interactions_to_customers
from app.src.spark.data.models import InteractionType, Interaction, Customer, Category, Product
from app.src.spark.agent.environment_v2 import UserBehaviorModel, RecommendationEnv
from stable_baselines3 import DQN
from torch import torch
import numpy as np
from datetime import datetime

router = APIRouter()

# Directories and model loading
model_dir = "app/src/spark/agent/models"
model_path = f"{model_dir}/dqn_recommender"
model = DQN.load(model_path)

# Load data
products, max_price, product_id_to_index = load_products()
num_products = len(products)
customers, customer_id_to_index = load_customers(num_products)

# Initialize environment with the same setup as in training
user_behavior_model = UserBehaviorModel(customers=customers, num_products=num_products)
env = RecommendationEnv(users=customers, products=products, top_k=5, max_price=max_price, user_behavior_model=user_behavior_model)


@router.get("/api/products")
async def get_products():
    """Fetch all products available in the catalog."""
    product_data = [{"id": p.idx, "name": p.name, "price": f"{p.price:.2f}", "desc": p.desc, "image": "product_image.png"} for p in products]
    return JSONResponse(content=product_data)


@router.get("/api/recommendations")
async def recommendations(user_id: int):
    """Generate top 5 product recommendations for a specific user after a major interaction."""
    try:
        # Reset the environment for the specified user
        obs = env.reset(user_idx=user_id)

        # Convert the observation to a tensor for the model
        obs_tensor, _ = model.policy.obs_to_tensor(obs)

        # Get the Q-values for each product from the model
        with torch.no_grad():
            q_values = model.q_net(obs_tensor)

        # Convert Q-values to numpy array and flatten
        q_values = q_values.cpu().numpy().flatten()

        # Get the indices of the top 5 products based on Q-values
        top_k_indices = np.argsort(q_values)[-5:][::-1]

        # Prepare the list of recommended products
        recommendations = [
            {
                "id": products[idx].idx,
                "name": products[idx].name,
                "price": f"{products[idx].price:.2f}",
                "desc": products[idx].desc,
                "image": "product_image.png",
            }
            for idx in top_k_indices
        ]

        return JSONResponse(content=recommendations)

    except IndexError:
        return JSONResponse(content={"error": "User not found"}, status_code=404)


@router.get("/api/catalogue")
async def catalogue(category_id: Optional[int] = None):
    """Fetch products by category if category_id is specified, otherwise all products."""
    filtered_products = [p for p in products if p.category.idx == category_id] if category_id else products
    catalogue_data = [{"id": p.idx, "name": p.name, "price": f"{p.price:.2f}", "desc": p.desc, "image": "product_image.png"} for p in filtered_products]
    return JSONResponse(content=catalogue_data)


@router.get("/api/user")
async def user(user_id: int):
    """Fetch user profile and interaction history."""
    customer_data, _ = load_customers(idxs=[user_id])
    if not customer_data:
        return JSONResponse(content={"error": "User not found"}, status_code=404)

    customer = customer_data[0]
    user_data = {
        "id": customer.idx,
        "city": customer.city,
        "state": customer.state,
        "zip_code": customer.zip_code,
        "interactions": [{"product_id": i.product_idx, "type": i.type.value, "value": i.value} for i in customer.interactions],
    }
    return JSONResponse(content=user_data)


@router.post("/api/interaction")
async def save_interaction(
    user_id: int,
    product_id: int,
    interaction_type: str,
    value: float,
    review_score: Optional[int] = None,
    zip_code: Optional[int] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
):
    """Save a new interaction, adding a new user if needed."""
    try:
        interaction_type_enum = InteractionType(interaction_type)
    except ValueError:
        return JSONResponse(content={"error": "Invalid interaction type"}, status_code=400)

    customer_idx = customer_id_to_index.get(user_id)

    if customer_idx is None:
        if zip_code is None or city is None or state is None:
            return JSONResponse(content={"error": "New customer requires zip_code, city, and state"}, status_code=400)

        customer_idx = add_customer(user_id, zip_code, city, state, customers, customer_id_to_index, num_products)

    # Record interaction
    interaction_id = len(env.interactions)
    timestamp = datetime.now()
    interaction_data = {
        "id": interaction_id,
        "timestamp": timestamp,
        "product_idx": product_id,
        "customer_idx": customer_idx,
        "type": interaction_type_enum,
        "value": value,
        "review_score": review_score,
    }

    save_interaction(interaction_data)
    assign_interactions_to_customers(customers, [interaction_data])

    return JSONResponse(content={"message": "Interaction saved successfully"})
