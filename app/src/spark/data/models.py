from typing import List, Optional
from datetime import datetime
from enum import Enum


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
        product_idx: int,
        customer_idx: int,
        type: InteractionType,
        value: float = 0.0,
        review_score: Optional[int] = None,
    ):
        self.idx = idx
        self.timestamp = timestamp
        self.product_idx = product_idx
        self.customer_idx = customer_idx
        self.type = type
        self.value = value
        self.review_score = review_score


class Customer:
    def __init__(self, idx: int, zip_code: int, city: str, state: str, num_products: int):
        self.idx = idx
        self.zip_code = zip_code
        self.city = city
        self.state = state
        self.views = [0] * num_products
        self.likes = [0] * num_products
        self.purchases = [0] * num_products
        self.ratings = [0] * num_products


class Category:
    def __init__(self, idx: int, name: str, desc: str):
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
