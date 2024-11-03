from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from typing import List, Optional
from app.src.spark.data.loader import load_products, load_customers
import json

router = APIRouter()

# API router
# use a switch statement to select the right agent
# and fetch the right data
#


# @router.get("/api")
# async def dummy_data():
#     data = [
#         {
#             "id": 1,
#             "name": "Product 1",
#             "price": "99.00",
#             "desc": "Description of Product 1 Description of Product 1 Description of Product 1 Description of Product 1 Description of Product 1 Description of Product 1Description of Product 1 Description of Product 1 Description of Product 1 Description of Product 1 Description of Product 1 Description of Product 1Description of Product 1 Description of Product 1 Description of Product 1 Description of Product 1 Description of Product 1 Description of Product 1Description of Product 1 Description of Product 1 Description of Product 1 Description of Product 1 Description of Product 1 Description of Product 1Description of Product 1 Description of Product 1 Description of Product 1 Description of Product 1 Description of Product 1 Description of Product 1Description of Product 1 Description of Product 1 Description of Product 1 Description of Product 1 Description of Product 1 Description of Product 1Description of Product 1 Description of Product 1 Description of Product 1 Description of Product 1 Description of Product 1 Description of Product 1",
#             "image": "featured_product.png",
#         },
#         {"id": 2, "name": "Product 2", "price": "20.99", "desc": "Description of Product 2", "image": "rec_product_img.png"},
#         {"id": 3, "name": "Product 3", "price": "23.99", "desc": "Description of Product 3", "image": "rec_product_img.png"},
#         {"id": 4, "name": "Product 4", "price": "64.99", "desc": "Description of Product 4", "image": "rec_product_img.png"},
#         {"id": 5, "name": "Product 5", "price": "22.99", "desc": "Description of Product 5", "image": "rec_product_img.png"},
#         {"id": 6, "name": "Product 6", "price": "61.99", "desc": "Description of Product 6", "image": "rec_product_img.png"},
#         {"id": 7, "name": "Product 7", "price": "96.99", "desc": "Description of Product 7", "image": "rec_product_img.png"},
#         {"id": 8, "name": "Product 8", "price": "27.99", "desc": "Description of Product 8", "image": "rec_product_img.png"},
#         {"id": 9, "name": "Product 9", "price": "11.99", "desc": "Description of Product 9", "image": "rec_product_img.png"},
#         {"id": 10, "name": "Product 10", "price": "45.99", "desc": "Description of Product 10", "image": "rec_product_img.png"},
#         {"id": 11, "name": "Product 11", "price": "22.99", "desc": "Description of Product 11", "image": "rec_product_img.png"},
#         {"id": 12, "name": "Product 12", "price": "85.99", "desc": "Description of Product 12", "image": "rec_product_img.png"},
#         {"id": 13, "name": "Product 13", "price": "61.99", "desc": "Description of Product 13", "image": "rec_product_img.png"},
#         {"id": 14, "name": "Product 14", "price": "34.99", "desc": "Description of Product 14", "image": "rec_product_img.png"},
#         {"id": 15, "name": "Product 15", "price": "98.99", "desc": "Description of Product 15", "image": "rec_product_img.png"},
#         {"id": 16, "name": "Product 16", "price": "46.99", "desc": "Description of Product 16", "image": "rec_product_img.png"},
#         {"id": 17, "name": "Product 17", "price": "23.99", "desc": "Description of Product 17", "image": "rec_product_img.png"},
#     ]
#     return data


@router.get("/api")
async def get_products():
    # Load all products from the data source
    products = load_products()
    # Format products as dictionaries for JSON response
    data = [{"id": p.idx, "name": p.name, "price": f"{p.price:.2f}", "desc": p.desc, "image": "product_image.png"} for p in products]
    return JSONResponse(content=data)


@router.get("/api/recommendations")
async def recommendations(user_id):
    # get recommendations for user with user_id
    # if no user id, get the default recommendation
    return []


@router.get("/api/catalogue")
async def catalogue(category_id: Optional[int] = None):
    # Load products filtered by category if category_id is provided
    products = load_products()
    if category_id:
        products = [p for p in products if p.category.idx == category_id]

    data = [{"id": p.idx, "name": p.name, "price": f"{p.price:.2f}", "desc": p.desc, "image": "product_image.png"} for p in products]
    return JSONResponse(content=data)


@router.get("/api/user")
async def user(user_id: int):
    # Load user data from the data source
    customers = load_customers(idxs=[user_id], include_interactions=True)
    if not customers:
        return JSONResponse(content={"error": "User not found"}, status_code=404)

    customer = customers[0]
    data = {
        "id": customer.idx,
        "city": customer.city,
        "state": customer.state,
        "zip_code": customer.zip_code,
        "interactions": [{"product_id": i.product_idx, "type": i.type.value, "value": i.value} for i in customer.interactions],
    }
    return JSONResponse(content=data)
