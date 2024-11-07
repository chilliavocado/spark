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
import traceback

data_dir = "app/src/spark/data/preprocessed_data/"
model_dir = "app/src/spark/agent/models/"


def load_csv(filename: str) -> pd.DataFrame:
    """Load a CSV file from the data directory."""
    return pd.read_csv(f"{data_dir}{filename}")


# Load customers with interactions if required
def load_customers(idxs: List[int] = [], include_interactions: bool = True) -> List[Customer]:
    customer_df = load_csv("Customer.csv")
    interaction_df = load_csv("Interaction.csv") if include_interactions else None

    if idxs:
        customer_df = customer_df[customer_df["idx"].isin(idxs)]

    customers = []
    num_products = 100  # Adjust as needed to match your dataset
    for _, row in customer_df.iterrows():
        interactions = []
        if include_interactions and interaction_df is not None:
            customer_interactions = interaction_df[interaction_df["customer_idx"] == row["idx"]]
            for _, int_row in customer_interactions.iterrows():
                interactions.append(
                    Interaction(
                        idx=str(int_row["idx"]),
                        timestamp=datetime.strptime(int_row["timestamp"], "%Y-%m-%d %H:%M:%S"),
                        customer_idx=int_row["customer_idx"],
                        product_idx=int_row["product_idx"],
                        type=InteractionType(int_row["type"]),
                        value=int_row["value"],
                        review_score=int_row["review_score"],
                    )
                )

        customer = Customer(idx=row["idx"], zip_code=row["zip_code"], city=row["city"], state=row["state"], interactions=interactions)
        # Initialize views, likes, buys, and ratings as numeric arrays
        customer.views = np.zeros(num_products, dtype=float)
        customer.likes = np.zeros(num_products, dtype=float)
        customer.buys = np.zeros(num_products, dtype=float)
        customer.ratings = np.zeros(num_products, dtype=float)

        customers.append(customer)

    return customers


def load_customer(idx: int) -> Optional[Customer]:
    customers = load_customers()
    for customer in customers:
        if customer.idx == idx:
            return customer
    return None


# Load products
def load_products() -> List[Product]:
    product_df = load_csv("Product.csv")
    category_df = load_csv("Category.csv")
    category_map = {row["idx"]: Category(idx=row["idx"], name=row["name"], desc=row["desc"]) for _, row in category_df.iterrows()}

    return [
        Product(
            idx=row["idx"],
            name=row["name"],
            desc=row["desc"],
            long_desc=row["long_desc"],
            category=category_map.get(row["category_num_id"]),
            price=row["price"],
        )
        for _, row in product_df.iterrows()
    ]


def load_product(idx: int) -> Optional[Product]:
    products = load_products()
    for product in products:
        if product.idx == idx:
            return product
    return None


# Load categories
def load_categories(idxs: List[int] = []) -> List[Category]:
    category_df = load_csv("Category.csv")
    if idxs:
        category_df = category_df[category_df["idx"].isin(idxs)]

    return [Category(idx=row["idx"], name=row["name"], desc=row["desc"]) for _, row in category_df.iterrows()]


# Load interactions
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


def get_recommendations(user_id: int) -> Optional[List[Dict]]:
    try:
        # Load the model
        model_path = f"{model_dir}/ppo_recommender"
        model = PPO.load(model_path)

        # Load customers, products, and interactions
        customer = load_customer(user_id)
        if not customer:
            print("Customer not found.")
            return None

        customers = load_customers()
        products = load_products()
        categories = load_categories()
        product_map = {product.idx: product for product in products}  # Create a map for quick lookup
        interactions = load_interactions()

        # Initialize the environment with required arguments
        env = RecommendationEnv(users=customers, products=products, categories=categories, top_k=10)

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
                product_idx=products[0].idx if products else 0,  # Choose a default product if available
                type=InteractionType.VIEW,
                value=1.0,
                review_score=0,
            )

        # Update the observation using the environment and last interaction
        obs = env.update_observation(customer, last_interaction)

        # Use the model to predict based on the observation
        recommended_product_indices, _ = model.predict(obs, deterministic=True)

        # Map recommended indices to actual products
        recommended_products = [
            {
                "id": product_map[idx].idx,
                "name": product_map[idx].name,
                "price": f"{product_map[idx].price:.2f}",
                "desc": product_map[idx].desc,
                "image": "product_image.png",
            }
            for idx in recommended_product_indices
            if idx in product_map
        ]

        return recommended_products

    except Exception as e:
        tb = traceback.format_exc()
        print(f"Error generating recommendations: {e}\n{tb}")
        return None
