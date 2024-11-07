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

data_dir = "app/src/spark/data/preprocessed_data/"


def load_customers(num_products: int, idxs: List[int] = []) -> Tuple[List[Customer], Dict[int, int]]:
    customer_df = pd.read_csv(f"{data_dir}Customer.csv")

    if idxs:
        customer_df = customer_df[customer_df["idx"].isin(idxs)]

    # Reset index to get zero-based indices
    customer_df.reset_index(drop=True, inplace=True)
    customer_id_to_index = {row["idx"]: idx for idx, row in customer_df.iterrows()}

    customers = [
        Customer(idx=idx, zip_code=str(row["zip_code"]), city=row["city"], state=row["state"], num_products=num_products) for idx, row in customer_df.iterrows()
    ]

    return customers, customer_id_to_index


def load_customer(idx: int) -> Optional[Customer]:
    customer_df = pd.read_csv(f"{data_dir}Customer.csv")
    row = customer_df[customer_df["idx"] == idx].iloc[0]
    customer = Customer(
        idx=row["idx"],
        zip_code=str(row["zip_code"]),
        city=row["city"],
        state=row["state"],
        interactions=assign_interactions_to_customers(customers, interactions),
    )
    return customer


def load_categories(idxs: List[int] = []) -> List[Category]:
    category_df = pd.read_csv(f"{data_dir}Category.csv")
    if idxs:
        category_df = category_df[category_df["idx"].isin(idxs)]

    categories = [Category(idx=row["idx"], name=row["name"], desc=row["desc"]) for _, row in category_df.iterrows()]
    return categories


def load_product(idx: int) -> Optional[Product]:
    product_df = pd.read_csv(f"{data_dir}Product.csv")
    category_df = pd.read_csv(f"{data_dir}Category.csv")

    # Create a dictionary to map category IDs to Category objects
    category_map = {row["idx"]: Category(idx=row["idx"], name=row["name"], desc=row["desc"]) for _, row in category_df.iterrows()}

    # Get the product row based on the index
    product_row = product_df[product_df["idx"] == idx]

    # If no product is found, return None
    if product_row.empty:
        return None

    row = product_row.iloc[0]

    product = Product(
        idx=row["idx"],  # Use zero-based index
        name=row["name"],
        desc=row["desc"],
        long_desc=row["long_desc"],
        category=category_map.get(row["category_num_id"]),
        price=row["price"],
    )

    # Convert category to a dictionary if it exists
    if product.category:
        product.category = {
            "id": product.category.idx,
            "name": product.category.name,
            "desc": product.category.desc,
        }

    return product


def load_products(idxs: List[int] = []) -> Tuple[List[Product], float, Dict[int, int]]:
    product_df = pd.read_csv(f"{data_dir}Product.csv")
    category_df = pd.read_csv(f"{data_dir}Category.csv")

    # Create a dictionary to map category IDs to Category objects
    category_map = {row["idx"]: Category(idx=row["idx"], name=row["name"], desc=row["desc"]) for _, row in category_df.iterrows()}

    if idxs:
        product_df = product_df[product_df["idx"].isin(idxs)]

    # Reset index to get zero-based indices
    product_df.reset_index(drop=True, inplace=True)
    product_id_to_index = {row["idx"]: idx for idx, row in product_df.iterrows()}

    products = [
        Product(
            idx=idx,  # Use zero-based index
            name=row["name"],
            desc=row["desc"],
            long_desc=row["long_desc"],
            category=category_map.get(row["category_num_id"]),
            price=row["price"],
        )
        for idx, row in product_df.iterrows()
    ]

    # Calculate the maximum price for setting price levels
    max_price = product_df["price"].max()
    return products, max_price, product_id_to_index


def load_interactions(product_id_to_index: Dict[int, int], customer_id_to_index: Dict[int, int]) -> List[Interaction]:
    interaction_df = pd.read_csv(f"{data_dir}Interaction.csv")

    interactions = []
    for _, row in interaction_df.iterrows():
        cust_id = row["customer_idx"]
        prod_id = row["product_idx"]

        if cust_id not in customer_id_to_index or prod_id not in product_id_to_index:
            continue  # Skip if customer or product not found

        interaction = Interaction(
            idx=row["idx"],
            timestamp=datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S"),
            customer_idx=customer_id_to_index[cust_id],
            product_idx=product_id_to_index[prod_id],
            type=InteractionType(row["type"]),
            value=row["value"],
            review_score=row["review_score"],
        )
        interactions.append(interaction)

    return interactions


def get_next_interaction_id():
    """Retrieve the next interaction ID based on the last entry in the UserInteractionLog.csv file."""
    file_path = f"{data_dir}/UserInteractionLog.csv"
    if not os.path.isfile(file_path):
        return 0  # Start from 0 if the file doesn't exist

    with open(file_path, mode="r") as file:
        lines = file.readlines()

    if len(lines) <= 1:
        # Only header exists or file is empty
        return 0

    last_line = lines[-1]
    last_id = int(last_line.split(",")[0])  # First column is the interaction ID
    return last_id + 1


def save_interaction(interaction_data):
    """Save interaction data to a separate interaction log file."""
    file_path = f"{data_dir}/UserInteractionLog.csv"

    # Check if the file exists and if it's empty
    file_exists = os.path.isfile(file_path)
    is_empty = not file_exists or os.path.getsize(file_path) == 0

    with open(file_path, mode="a", newline="") as file:
        writer = csv.writer(file)
        if is_empty:
            # Write the header
            writer.writerow(
                [
                    "id",
                    "timestamp",
                    "idx",
                    "product_idx",
                    "customer_idx",
                    "review_score",
                    "type",
                    "value",
                ]
            )
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


def assign_interactions_to_customers(customers, interactions):
    """Assigns a list of interaction dictionaries to respective customers."""
    for interaction in interactions:
        customer = customers[interaction["customer_idx"]]
        product_idx = interaction["product_idx"]
        interaction_type = interaction["type"]

        if interaction_type == InteractionType.VIEW:
            customer.views[product_idx] += 1
        elif interaction_type == InteractionType.LIKE:
            customer.likes[product_idx] += 1
        elif interaction_type == InteractionType.BUY:
            customer.purchases[product_idx] += 1
            if interaction["review_score"]:
                customer.ratings[product_idx] = interaction["review_score"]
        elif interaction_type == InteractionType.RATE:
            if interaction["review_score"]:
                customer.ratings[product_idx] = interaction["review_score"]


def assign_interactions_to_customer(customer):
    """Assigns a list of interaction dictionaries to a customer."""
    interactions = pd.read_csv(f"{data_dir}/Interaction.csv")
    interactions = interactions[interactions["customer_idx"] == customer.idx]

    for _, interaction in interactions.iterrows():
        product_idx = interaction["product_idx"]
        interaction_type = interaction["type"]

        if interaction_type == InteractionType.VIEW:
            customer.views[product_idx] += 1
        elif interaction_type == InteractionType.LIKE:
            customer.likes[product_idx] += 1
        elif interaction_type == InteractionType.BUY:
            customer.buys[product_idx] += 1
            if interaction["review_score"]:
                customer.ratings[product_idx] = interaction["review_score"]
        elif interaction_type == InteractionType.RATE:
            if interaction["review_score"]:
                customer.ratings[product_idx] = interaction["review_score"]

    return customer


def add_customer(user_id, zip_code, city, state, customers, customer_id_to_index):
    new_customer_idx = len(customers)
    new_customer = Customer(idx=new_customer_idx, zip_code=zip_code, city=city, state=state)
    customers.append(new_customer)
    customer_id_to_index[user_id] = new_customer_idx

    with open(f"{data_dir}/Customer.csv", "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([new_customer_idx, user_id, zip_code, city, state])

    return new_customer_idx


def create_observation(user: Customer, num_products: int, categories: List[Category], interactions: List[Interaction]):
    """Create an observation for a given user based on their most recent interactions."""
    # Initialize the observation with zeros or default values
    obs = {
        "pref_prod": np.zeros(num_products),
        "pref_cat": np.zeros(len(categories)),
        "buys": np.zeros(num_products),
        "views": np.zeros(num_products),
        "likes": np.zeros(num_products),
        "ratings": np.zeros(num_products, dtype=np.float32),
        "product": np.zeros(num_products),
        "interaction": np.zeros(len(list(InteractionType))),
        "rating": 0,
    }

    # Load interactions specific to the current user
    user_interactions = [interaction for interaction in interactions if interaction.customer_idx == user.idx]

    if user_interactions:
        # Populate observation based on interactions
        for interaction in user_interactions:
            pid = interaction.product_idx
            if interaction.type == InteractionType.VIEW:
                obs["views"][pid] += 1
            elif interaction.type == InteractionType.LIKE:
                obs["likes"][pid] += 1
            elif interaction.type == InteractionType.BUY:
                obs["buys"][pid] += 1
            elif interaction.type == InteractionType.RATE:
                obs["ratings"][pid] = interaction.review_score or 0  # Default to 0 if review_score is None

        # Calculate preferences dynamically
        obs["pref_prod"] = get_product_preferences(user)
        obs["pref_cat"] = get_category_preferences(user, categories, num_products)

    else:
        # For new users, generate a default observation with minimal preferences
        obs["pref_prod"] = np.random.random(num_products)
        obs["pref_cat"] = np.random.random(len(categories))
        obs["views"] = np.random.randint(0, 2, num_products)  # Simulate minimal views

    return obs


def get_product_preferences(user: Customer):
    # Calculate preferences based on past interactions
    view_prefs = np.array(user.views) / 20
    purchase_prefs = np.array(user.buys)
    like_prefs = np.array(user.likes) / 15
    rating_prefs = np.array(user.ratings)
    rating_prefs[rating_prefs > 0] -= 2

    product_prefs = view_prefs + purchase_prefs + like_prefs + rating_prefs
    return product_prefs


def get_category_preferences(user: Customer, categories: List[Category], num_products: int):
    prod_prefs = get_product_preferences(user)
    cat_prefs = np.zeros(len(categories), np.float32)

    for idx, prod_pref in enumerate(prod_prefs):
        if prod_pref > 0:
            product = user.buys[idx]  # Assuming `products` list is accessible here
            cat_idx = product.category.idx
            cat_prefs[cat_idx] += prod_pref

    cat_prefs = cat_prefs / 5  # Normalize if needed
    return cat_prefs


def get_recommendations(user_id: int):
    try:
        # Load the pre-trained PPO model
        model_path = "app/src/spark/agent/models/ppo_recommender"
        model = PPO.load(model_path)

        # Load the customers, products, and interactions
        customers, customer_id_to_index = load_customers(num_products=0)
        products, _, _ = load_products()
        interactions = load_interactions(product_id_to_index={}, customer_id_to_index=customer_id_to_index)

        user_idx = customer_id_to_index.get(user_id)
        if user_idx is None:
            return None  # User not found

        # Get the current customer
        user = customers[user_idx]

        # Create the observation using the helper function
        obs = create_observation(user, len(products), categories=load_categories(), interactions=interactions)

        # Use model.predict to get the action
        action, _ = model.predict(obs, deterministic=True)

        # Prepare the list of recommended products
        recommended_product_indices = action if isinstance(action, (list, np.ndarray)) else [action]
        recommendations = [
            {
                "id": products[idx].idx,
                "name": products[idx].name,
                "price": f"{products[idx].price:.2f}",
                "desc": products[idx].desc,
                "image": "product_image.png",
            }
            for idx in recommended_product_indices
            if idx < len(products)
        ]

        return recommendations

    except Exception as e:
        print(f"Error generating recommendations: {e}")
        return None
