# loader.py

import pandas as pd
from datetime import datetime
from typing import List, Tuple, Dict, Optional
from app.src.spark.data.models import Customer, Category, Product, Interaction, InteractionType
import csv
import numpy as np
import torch

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
    customer = Customer(idx=row["idx"], zip_code=str(row["zip_code"]), city=row["city"], state=row["state"], num_products=0)
    return customer


def load_categories(idxs: List[int] = []) -> List[Category]:
    category_df = pd.read_csv(f"{data_dir}Category.csv")
    if idxs:
        category_df = category_df[category_df["idx"].isin(idxs)]

    categories = [Category(idx=row["idx"], name=row["name"], desc=row["desc"]) for _, row in category_df.iterrows()]
    return categories


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


def load_product(idx: int) -> Optional[Product]:
    product_df = pd.read_csv(f"{data_dir}Product.csv")
    category_df = pd.read_csv(f"{data_dir}Category.csv")

    # Create a dictionary to map category IDs to Category objects
    category_map = {row["idx"]: Category(idx=row["idx"], name=row["name"], desc=row["desc"]) for _, row in category_df.iterrows()}

    # Get the product row based on the index
    row = product_df[product_df["idx"] == idx].iloc[0]

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


def save_interaction(interaction_data):
    with open(f"{data_dir}/Interaction.csv", "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                interaction_data["id"],
                interaction_data["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                f"order-{interaction_data['id']}",
                interaction_data["product_idx"],
                interaction_data["customer_idx"],
                interaction_data["review_score"] or 0,
                interaction_data["type"].value,
                interaction_data["value"],
            ]
        )


def add_customer(user_id, zip_code, city, state, customers, customer_id_to_index, num_products):
    new_customer_idx = len(customers)
    new_customer = Customer(idx=new_customer_idx, zip_code=zip_code, city=city, state=state, num_products=num_products)
    customers.append(new_customer)
    customer_id_to_index[user_id] = new_customer_idx

    with open(f"{data_dir}/Customer.csv", "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([new_customer_idx, user_id, zip_code, city, state])

    return new_customer_idx


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


def get_recommendations(
    user_id: int, customers: List[Customer], customer_id_to_index: Dict[int, int], products: List[Product], model, env, top_k: int = 5
) -> Optional[List[Dict]]:
    """Generate top_k product recommendations for a specific user."""
    try:
        user_idx = customer_id_to_index.get(user_id)
        if user_idx is None:
            return None  # User not found

        # Reset the environment for the specified user
        obs = env.reset(user_idx=user_idx)

        # Convert the observation to a tensor for the model
        obs_tensor, _ = model.policy.obs_to_tensor(obs)

        # Get the Q-values for each product from the model
        with torch.no_grad():
            q_values = model.q_net(obs_tensor)

        # Convert Q-values to numpy array and flatten
        q_values = q_values.cpu().numpy().flatten()

        # Get the indices of the top_k products based on Q-values
        top_k_indices = np.argsort(q_values)[-top_k:][::-1]

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

        return recommendations

    except Exception as e:
        print(f"Error generating recommendations: {e}")
        return None
