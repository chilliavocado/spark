
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/product", response_class=HTMLResponse)
async def product(request: Request, pid: int):
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
    
    selected_product = products[pid-1]  # dummy data, to be fetch from recommendation api
    rec_products = products[1:5]    # dummy data, to be fetch from recommendation api

    return templates.TemplateResponse("product.html",{"request": request, "selected_product": selected_product, "rec_products": rec_products})
