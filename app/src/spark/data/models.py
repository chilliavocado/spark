from typing import List

class Customer:
    def __init__(self, idx: int, city:str, purchases:List[int], views:List[int], likes:List[int], ratings:List[int]) -> None:
        self.idx = idx                  # user idx as id from the db
        self.city = city                # city where the customer is regisgtered
        self.purchases = purchases      # number of purchases for each product. format [0,4,0,2]
        self.views = views              # number of views for each product. format [0,30,23,3]
        self.likes = likes              # like for each product. format [0,1,0,1]
        self.ratings = ratings          # max rating(0-5)for each product. format [0,1,4,2,0]
        
class Category:
    """ Product category """
    def __init__(self, idx:int, name:str, desc:str) -> None:
        self.idx = idx                  # category idx as id from the db
        self.name = name                # name of the category
        self.desc = desc                # description of the category
        
class Product:
    def __init__(self, idx:int, name:str, desc:str, long_desc:str, category:Category, price:float) -> None:
        self.idx = idx                  # product idx as id from the db
        self.desc = desc                # description of the product
        self.long_desc = long_desc      # long description of the product
        self.name = name                # name of the product
        self.category = category        # category idx as id from the db
        self.price = price              # highest price (RRP) of the product (lower may due to discount)
                       
        
from datetime import datetime
from enum import Enum

# static list of available interactions
class InteractionType(Enum):
    VIEW = "view"
    LIKE = "like"
    BUY = "buy"
    RATE = "rate"
    EXIT = "exit"
    SESSION_START = "session_start"
    SESSION_CLOSE = "session_close"
    
class Interaction:
    def __init__(self, idx:int, timestamp:datetime, user:Customer, product:Product, type:InteractionType, value:int=None) -> None:
        self.idx = idx
        self.timestamp = timestamp
        self.user = user
        self.product = product          # load the priced at purchase, not the actual product RRP
        self.type = type
        self.value = value