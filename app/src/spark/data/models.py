from typing import List, Optional
from datetime import datetime
from enum import Enum


# static list of available interactions
class InteractionType(Enum):
    NONE = "none"
    VIEW = "view"
    LIKE = "like"
    BUY = "buy"
    RATE = "rate"
    EXIT = "exit"
    SESSION_START = "session_start"
    SESSION_CLOSE = "session_close"


class Interaction:
    def __init__(
        self,
        idx: str,
        timestamp: datetime,
        customer_idx: int,
        product_idx: int,
        type: InteractionType,
        value: Optional[float] = None,
        review_score: Optional[int] = None,
        city_embedding: Optional[List[int]] = None,
        state_embedding: Optional[List[int]] = None,
        zip_code_embedding: Optional[List[int]] = None,
        product_purchase_history: Optional[List[float]] = None,
        category_purchase_history: Optional[List[float]] = None,
        rate_history: Optional[List[float]] = None,
    ) -> None:
        self.idx = idx
        self.timestamp = timestamp
        self.customer_idx = customer_idx
        self.product_idx = product_idx
        self.type = type
        self.value = value
        self.review_score = review_score
        self.city_embedding = city_embedding
        self.state_embedding = state_embedding
        self.zip_code_embedding = zip_code_embedding
        self.product_purchase_history = product_purchase_history
        self.category_purchase_history = category_purchase_history
        self.rate_history = rate_history


class Customer:
    def __init__(self, idx: int, zip_code: int, city: str, state: str, interactions: Optional[List[Interaction]] = None) -> None:
        self.idx = idx
        self.zip_code = zip_code
        self.city = city
        self.state = state
        self.buys = []  # number of purchases for each product. format [0,4,0,2]
        self.views = []  # number of views for each product. format [0,30,23,3]
        self.likes = []  # like for each product. format [0,1,0,1]
        self.ratings = []  # max rating(0-5)for each product. format [0,1,4,2,0]
        self.interactions = interactions if interactions is not None else []


class Category:
    def __init__(self, idx: int, name: str, desc: str) -> None:
        self.idx = idx
        self.name = name
        self.desc = desc


class Product:
    def __init__(self, idx: int, name: str, desc: str, long_desc: str, category: Category, price: float) -> None:
        self.idx = idx
        self.name = name
        self.desc = desc
        self.long_desc = long_desc
        self.category = category
        self.price = price


"""
Previous code:
"""
# # static list of available interactions
# class InteractionType(Enum):
#     NONE = "none"
#     VIEW = "view"
#     LIKE = "like"
#     BUY = "buy"
#     RATE = "rate"
#     EXIT = "exit"
#     SESSION_START = "session_start"
#     SESSION_CLOSE = "session_close"


# class Interaction:
#     def __init__(self, idx: int, timestamp: datetime, customer_idx: int, product_idx: int, type: InteractionType, value: int = None) -> None:
#         self.idx = idx
#         self.timestamp = timestamp
#         self.customer_idx = customer_idx
#         self.product_idx = product_idx  # load the priced at purchase, not the actual product RRP
#         self.type = type
#         self.value = value


# class Customer:
#     def __init__(
#         self, idx: int, city: str, purchases: List[int], views: List[int], likes: List[int], ratings: List[int], interactions: List[Interaction]
#     ) -> None:
#         self.idx = idx  # user idx as id from the db
#         self.city = city  # city where the customer is regisgtered
#         self.purchases = purchases  # number of purchases for each product. format [0,4,0,2]
#         self.views = views  # number of views for each product. format [0,30,23,3]
#         self.likes = likes  # like for each product. format [0,1,0,1]
#         self.ratings = ratings  # max rating(0-5)for each product. format [0,1,4,2,0]
#         self.interactions = interactions


# class Category:
#     """Product category"""

#     def __init__(self, idx: int, name: str, desc: str) -> None:
#         self.idx = idx  # category idx as id from the db
#         self.name = name  # name of the category
#         self.desc = desc  # description of the category


# class Product:
#     def __init__(self, idx: int, name: str, desc: str, long_desc: str, category: Category, price: float) -> None:
#         self.idx = idx  # product idx as id from the db
#         self.desc = desc  # description of the product
#         self.long_desc = long_desc  # long description of the product
#         self.name = name  # name of the product
#         self.category = category  # category object associated with product
#         self.price = price  # highest price (RRP) of the product (lower may due to discount)
