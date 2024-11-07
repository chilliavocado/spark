from typing import List
from datetime import datetime
import pandas as pd
import ast
from spark.data.models import Customer, Category, Product, Interaction, InteractionType


data_dir = "../app/src/spark/data/preprocessed_data/"
model_dir = "../app/src/spark/agent/models/"

def load_csv(filename: str) -> pd.DataFrame:
    """Load a CSV file from the data directory."""
    return pd.read_csv(f"{data_dir}{filename}")


def load_customers(idxs: List[int] = [], include_interactions: bool = False) -> List[Customer]:
    customer_df = load_csv("Customer.csv")
    interaction_df = load_csv("Interaction.csv") if include_interactions else None

    if idxs:
        customer_df = customer_df[customer_df["idx"].isin(idxs)]

    customers = []
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
        customers.append(customer)

    return customers



def parse_vector_field(field: str) -> List[float]:
    try:
        return ast.literal_eval(field) if field else []
    except (ValueError, SyntaxError):
        return []


def load_interactions(idxs: List[int] = [], customer_idxs: List[int] = [], k: int = 0) -> List[Interaction]:
    interaction_df = pd.read_csv("../app/src/spark/data/preprocessed_data/Customer_Interactions.csv")

    if idxs:
        interaction_df = interaction_df[interaction_df["idx"].isin(idxs)]
    elif customer_idxs:
        interaction_df = interaction_df[interaction_df["customer_idx"].isin(customer_idxs)]

    if k > 0:
        interaction_df = interaction_df.sort_values(by="timestamp", ascending=False).head(k)

    interactions = []
    for _, row in interaction_df.iterrows():
        interactions.append(
            Interaction(
                idx=row["idx"],
                timestamp=datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S"),
                customer_idx=row["customer_idx"],
                product_idx=row["product_idx"],
                type=InteractionType(row["type"]),
                value=row["value"],
                review_score=row["review_score"],
                city_embedding=parse_vector_field(row["city_embedding"]),
                state_embedding=parse_vector_field(row["state_embedding"]),
                zip_code_embedding=parse_vector_field(row["zip_code_embedding"]),
                product_purchase_history=parse_vector_field(row["product_purchase_history"]),
                category_purchase_history=parse_vector_field(row["category_purchase_history"]),
                rate_history=parse_vector_field(row["rate_history"]),
            )
        )
    return interactions


def store_interactions(interactions: List[Interaction]):
    interaction_data = [
        {
            "idx": i.idx,
            "timestamp": i.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "customer_idx": i.customer_idx,
            "product_idx": i.product_idx,
            "type": i.type.value,
            "value": i.value,
            "review_score": i.review_score,
        }
        for i in interactions
    ]
    interaction_df = pd.DataFrame(interaction_data)
    interaction_df.to_csv("../app/src/spark/data/preprocessed_data/Interaction.csv", index=False)


def load_categories(idxs: List[int] = []) -> List[Category]:
    category_df = pd.read_csv("../app/src/spark/data/preprocessed_data/Category.csv")
    if idxs:
        category_df = category_df[category_df["idx"].isin(idxs)]

    categories = [Category(idx=row["idx"], name=row["name"], desc=row["desc"]) for _, row in category_df.iterrows()]
    return categories


def load_products(idxs: List[int] = []) -> List[Product]:
    product_df = pd.read_csv("../app/src/spark/data/preprocessed_data/Product.csv")
    category_df = pd.read_csv("../app/src/spark/data/preprocessed_data/Category.csv")

    category_map = {row["idx"]: Category(idx=row["idx"], name=row["name"], desc=row["desc"]) for _, row in category_df.iterrows()}

    if idxs:
        product_df = product_df[product_df["idx"].isin(idxs)]

    products = []
    for _, row in product_df.iterrows():
        category = category_map.get(row["category_num_id"])
        products.append(Product(idx=row["idx"], name=row["name"], desc=row["desc"], long_desc=row["long_desc"], category=category, price=row["price"]))
    return products


"""
Template code:
"""
# def load_customers(idxs: List[int] = [], include_interactions=False) -> List[Customer]:
#     customers = []
#     # TODO: get a list of customers with given idx list
#     # If list is empty, return all customers
#     # else return a subject filtered by idxs
#     for idx in idxs:
#         # TODO: construct Customer objects and add to list
#         pass

#     if include_interactions:
#         # load interaction for this customer
#         pass

#     return customers


# def load_interactions(idxs: List[int] = [], customer_idxs: List[int] = [], k: int = 0) -> List[Interaction]:
#     interactions = []
#     # TODO: get a list of interactoins with given idx list
#     # If list is empty, return all interactions
#     # else return a subject filtered by idxs
#     # if k > 0, return the most recent k interactions

#     for idx in idxs:
#         # TODO: construct Interaction and related objects and add to list
#         pass

#     for c_idx in customer_idxs:
#         # TODO: construct Interaction and related objects and add to list
#         pass

#     return interactions


# def store_interactions(interactions: List[Interaction]):
#     # TODO: store interactions into file
#     pass


# def load_categories(idxs: List[int] = []) -> List[Category]:
#     # TODO: get categoires in objects from the db
#     # If list is empty, return all categories
#     # else return a subject filtered by idxs
#     # Object type spark.data.model.Category
#     categories = []

#     for idx in idxs:
#         # TODO: construct Category objects and add to list
#         pass

#     return categories


# def load_category_names(idxs: List[int] = []) -> List[str]:
#     # TODO: get a list of cat names in order if idx
#     # If list is empty, return all categories
#     # else return a subject filtered by idxs
#     names = []  # list of strings of cat names

#     return names


# def load_products(idxs: List[int] = []) -> List[Product]:
#     products = []
#     # TODO: get a list of products with given idx list
#     # If list is empty, return all products
#     # else return a subject filtered by idxs
#     for idx in idxs:
#         # TODO: construct Produc and related objects objects and add to list
#         pass

#     return products
