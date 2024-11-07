# loader.py

import os
import pandas as pd
from datetime import datetime
from typing import List, Tuple, Dict, Optional
from app.src.spark.data.models import Customer, Category, Product, Interaction, InteractionType
import csv
import numpy as np
import torch
from app.src.spark import utils
from stable_baselines3 import PPO
from app.src.spark.agent.environment import RecommendationEnv

data_dir = "app/src/spark/data/preprocessed_data/"
model_dir = "app/src/spark/agent/models/"


def load_csv(filename: str) -> pd.DataFrame:
    """Load a CSV file from the data directory."""
    return pd.read_csv(f"{data_dir}{filename}")


# Loading single and multiple customers
def load_customers() -> Dict[int, Customer]:
    customer_df = load_csv("Customer.csv")
    return {row["idx"]: Customer(idx=row["idx"], zip_code=str(row["zip_code"]), city=row["city"], state=row["state"]) for _, row in customer_df.iterrows()}


def load_customer(idx: int) -> Optional[Customer]:
    customers = load_customers()
    return customers.get(idx)


# Loading single and multiple products
def load_products() -> Dict[int, Product]:
    product_df = load_csv("Product.csv")
    category_df = load_csv("Category.csv")
    category_map = {row["idx"]: {"id": row["idx"], "name": row["name"], "desc": row["desc"]} for _, row in category_df.iterrows()}

    return {
        row["idx"]: Product(
            idx=row["idx"],
            name=row["name"],
            desc=row["desc"],
            long_desc=row["long_desc"],
            category=category_map.get(row["category_num_id"]),
            price=row["price"],
        )
        for _, row in product_df.iterrows()
    }


def load_product(idx: int) -> Optional[Product]:
    products = load_products()
    return products.get(idx)


def load_categories(idxs: List[int] = []) -> List[Category]:
    category_df = load_csv("Category.csv")
    if idxs:
        category_df = category_df[category_df["idx"].isin(idxs)]

    categories = [Category(idx=row["idx"], name=row["name"], desc=row["desc"]) for _, row in category_df.iterrows()]
    return categories


def load_interactions() -> List[Interaction]:
    interaction_df = load_csv("Interaction.csv")
    return [
        Interaction(
            idx=row["idx"],
            timestamp=datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S"),
            customer_idx=row["customer_idx"],
            product_idx=row["product_idx"],
            type=InteractionType(row["type"]),
            value=row["value"],
            review_score=row["review_score"],
        )
        for _, row in interaction_df.iterrows()
    ]


def get_next_interaction_id() -> int:
    """Retrieve the next interaction ID based on the last entry in the UserInteractionLog.csv file."""
    file_path = f"{data_dir}/UserInteractionLog.csv"
    if not os.path.isfile(file_path):
        return 0

    with open(file_path, mode="r") as file:
        lines = file.readlines()

    return int(lines[-1].split(",")[0]) + 1 if len(lines) > 1 else 0


def save_interaction(interaction_data: Dict):
    """Save interaction data to a separate interaction log file."""
    file_path = f"{data_dir}/UserInteractionLog.csv"
    is_empty = not os.path.isfile(file_path) or os.path.getsize(file_path) == 0

    with open(file_path, mode="a", newline="") as file:
        writer = csv.writer(file)
        if is_empty:
            writer.writerow(["id", "timestamp", "idx", "product_idx", "customer_idx", "review_score", "type", "value"])
        writer.writerow(
            [
                interaction_data["id"],
                interaction_data["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                interaction_data["idx"],
                interaction_data["product_idx"],
                interaction_data["customer_idx"],
                interaction_data["review_score"],
                interaction_data["type"],
                interaction_data["value"],
            ]
        )


def get_product_preferences(obs: Dict) -> np.ndarray:
    weights = {"views": 0.2, "buys": 1.0, "likes": 0.3, "ratings": 0.5}

    max_views = np.max(obs["views"]) if np.max(obs["views"]) > 0 else 1
    max_buys = np.max(obs["buys"]) if np.max(obs["buys"]) > 0 else 1
    max_likes = np.max(obs["likes"]) if np.max(obs["likes"]) > 0 else 1
    max_ratings = np.max(obs["ratings"]) if np.max(obs["ratings"]) > 0 else 1

    product_prefs = (
        (obs["views"] / max_views) * weights["views"]
        + (obs["buys"] / max_buys) * weights["buys"]
        + (obs["likes"] / max_likes) * weights["likes"]
        + (obs["ratings"] / max_ratings) * weights["ratings"]
    )

    return product_prefs


def get_category_preferences(obs: Dict, categories: List[int], num_products: int) -> np.ndarray:
    cat_prefs = np.zeros(len(categories), np.float32)

    for idx, val in enumerate(obs["pref_prod"]):
        if val > 0:
            cat_idx = idx % len(categories)
            cat_prefs[cat_idx] += val

    total_pref = np.sum(cat_prefs)
    if total_pref > 0:
        cat_prefs = cat_prefs / total_pref

    return cat_prefs


def get_recommendations(user_id: int) -> Optional[List[Dict]]:
    try:
        model_path = f"{model_dir}/ppo_recommender"
        model = PPO.load(model_path)

        # Load the customer
        customer = load_customer(user_id)
        if not customer:
            return None

        # Load products, categories, and interactions
        products = load_products()
        categories = load_categories()
        interactions = load_interactions()

        # Initialize the environment
        env = RecommendationEnv(users=[customer], products=list(products.values()), categories=categories, top_k=10)

        # Simulate or find the last interaction for the user
        user_interactions = [i for i in interactions if i.customer_idx == user_id]
        if user_interactions:
            last_interaction = user_interactions[-1]
        else:
            # Simulate a last interaction if none exists
            last_interaction = Interaction(
                idx="0",
                timestamp=datetime.now(),
                customer_idx=user_id,
                product_idx=next(iter(products)).idx,  # Choose a default product
                type=InteractionType.VIEW,
                value=1.0,
                review_score=0,
            )

        # Update the observation using the environment and last interaction
        obs = env.update_observation(customer, last_interaction)

        # Use the model to predict based on the observation
        recommended_products, _ = model.predict(obs, deterministic=True)

        # Prepare and return the list of recommended products
        return [
            {
                "id": products[idx].idx,
                "name": products[idx].name,
                "price": f"{products[idx].price:.2f}",
                "desc": products[idx].desc,
                "image": "product_image.png",
            }
            for idx in recommended_products[:5]
            if idx in products
        ]

    except Exception as e:
        print(f"Error generating recommendations: {e}")
        return None
