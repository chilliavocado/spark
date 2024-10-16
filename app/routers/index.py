# app/routers/products.py

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    products = [] # dummy product data  

    # construct api url dynamically
    host = request.client.host
    port = "8000" # request.client.port not working!
    scheme = request.scope["scheme"]
    api_url = f"{scheme}://{host}:{port}/api"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(api_url)
        if response.status_code == 200:
            products = response.json()
        else:
            print("Error fetching data:", response.status_code)
            products = [{"ERROR CODE": response.status_code, "Message": response.reason_phrase}]
    
    featured_product = products[0]  # dummy data, to be fetch from recommendation api
    rec_products = products[1:5]    # dummy data, to be fetch from recommendation api
    cat_products = products         # dummy data, to be fetch from catalogue api

    return templates.TemplateResponse("index.html",{"request": request, "featured_product": featured_product, "rec_products": rec_products, "cat_products": cat_products})
