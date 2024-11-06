# product.py

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import httpx

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

DEFAULT_USER_ID = 0


@router.get("/product/{product_id}", response_class=HTMLResponse)
async def product_detail(request: Request, product_id: int):
    """Fetch product details for the product page."""
    base_url = request.base_url
    base_api_url = f"{base_url}api"

    # Define API endpoints
    product_url = f"{base_api_url}/product?product_id={product_id}"  # corrected URL
    recommendations_url = f"{base_api_url}/recommendations?user_id={DEFAULT_USER_ID}"

    async with httpx.AsyncClient() as client:
        # Fetch product details
        product_response = await client.get(product_url)
        # Fetch recommendations
        recommendations_response = await client.get(recommendations_url)

    if product_response.status_code == 200:
        selected_product = product_response.json()
        rec_products = recommendations_response.json()[:5] if recommendations_response.status_code == 200 else []

        return templates.TemplateResponse(
            "product.html",
            {
                "request": request,
                "selected_product": selected_product,
                "rec_products": rec_products,
                "user_id": DEFAULT_USER_ID,  # Ensure user_id is passed
            },
        )
    else:
        return JSONResponse(content={"error": "Product not found"}, status_code=404)
