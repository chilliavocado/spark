# loader.py

import os
import pandas as pd
from datetime import datetime
from typing import List, Tuple, Dict, Optional
from app.src.spark.data.models import Customer, Category, Product, Interaction, InteractionType
import csv
import numpy as np
from app.src.spark import utils
from stable_baselines3 import PPO, A2C
from app.src.spark.agent.environment import RecommendationEnv
import traceback

data_dir = "app/src/spark/data/preprocessed_data/"
model_dir = "app/src/spark/agent/models/"

current_user_id = 0


def set_current_user(user_id: int):
    """Set the current user ID for server use."""
    global current_user_id
    current_user_id = user_id
    print(f"User ID set to: {user_id}")  # Debug log


def get_current_user() -> int:
    """Fetch the current user ID."""
    print(f"Fetching current user ID: {current_user_id}")  # Debug log
    return current_user_id


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
    """Save interaction data to a separate interaction log file and update the environment observation."""
    file_path = f"{data_dir}/UserInteractionLog.csv"
    is_empty = not os.path.isfile(file_path) or os.path.getsize(file_path) == 0

    # Save interaction data to CSV
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

    # Find the corresponding customer in the environment
    customer_idx = interaction_data["customer_idx"]
    customer = next((user for user in env.users if user.idx == customer_idx), None)

    # Ensure the customer exists in the environment before updating
    if customer:
        # Create an Interaction instance from interaction_data for updating the observation
        interaction = Interaction(
            idx=interaction_data["idx"],
            timestamp=interaction_data["timestamp"],
            customer_idx=interaction_data["customer_idx"],
            product_idx=interaction_data["product_idx"],
            type=InteractionType(interaction_data["type"]),
            value=interaction_data["value"],
            review_score=interaction_data["review_score"],
        )

        # Update the observation in the environment
        updated_obs = env.update_observation(customer, interaction)


def get_last_interaction(customer_idx: int) -> Optional[Interaction]:
    """Retrieve the last interaction for a specific customer from UserInteractionLog.csv."""
    interaction = load_csv("UserInteractionLog.csv")
    interaction = interaction[interaction["customer_idx"] == customer_idx]
    if interaction.empty:
        return None

    interaction = interaction.iloc[-1]
    return Interaction(
        idx=interaction["id"],
        timestamp=datetime.strptime(interaction["timestamp"], "%Y-%m-%d %H:%M:%S"),
        customer_idx=interaction["customer_idx"],
        product_idx=interaction["product_idx"],
        type=InteractionType(interaction["type"]),
        value=interaction["value"],
        review_score=interaction["review_score"],
    )


def get_model_and_env() -> Tuple[A2C, RecommendationEnv]:
    """Load the model and environment for generating recommendations."""
    model_path = f"{model_dir}/a2c_model"
    model = A2C.load(model_path)

    # Load customers, products, and interactions
    customers = load_customers()
    products = load_products()
    categories = load_categories()
    product_map = {product.idx: product for product in products}  # Create a map for quick lookup

    # Initialize the environment with required arguments
    env = RecommendationEnv(users=customers, products=products, categories=categories, top_k=10)
    env.seed(100)

    return model, env


# Load the model and environment once for reuse
model, env = get_model_and_env()


def get_recommendations(user_id: int) -> Optional[List[Dict]]:
    try:
        customer = env.users[user_id]
        products = env.products
        product_map = {product.idx: product for product in products}  # Create a map for quick lookup

        # Get the last interaction or create a default one if not found
        interaction = get_last_interaction(user_id)
        if not interaction:
            # Create a default interaction if none exists
            interaction = Interaction(
                idx="0",
                timestamp=datetime.now(),
                customer_idx=user_id,
                product_idx=products[0].idx if products else 0,  # Choose a default product if available
                type=InteractionType.NONE,
                value=1.0,
                review_score=0,
            )

        # Update the observation using the environment and interaction
        obs = env.update_observation(customer, interaction)

        # Use the model to predict based on the observation
        recommended_product_indices, _ = model.predict(obs, deterministic=True)

        # Map recommended indices to actual products
        recommended_products = [
            {
                "id": product_map[idx].idx,
                "name": product_map[idx].name,
                "price": f"{product_map[idx].price:.2f}",
                "desc": product_map[idx].desc,
                "image": f"{product_map[idx].category.name}.jpeg" if product_map[idx].category else "default.jpeg",
            }
            for idx in recommended_product_indices
            if idx in product_map
        ]

        return recommended_products

    except Exception as e:
        tb = traceback.format_exc()
        print(f"Error generating recommendations: {e}\n{tb}")
        return None
