# index.py

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# Default user ID placeholder; replace or dynamically set as needed
DEFAULT_USER_ID = 0


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Fetches products and recommendations data for the homepage."""
    base_url = request.base_url
    # print(f"Base URL: {base_url}")
    base_api_url = f"{base_url}api"
    # print(f"API URL: {base_api_url}")

    # Define API endpoints
    products_url = f"{base_api_url}/products"
    recommendations_url = f"{base_api_url}/recommendations?user_id={DEFAULT_USER_ID}"
    catalogue_url = f"{base_api_url}/catalogue"

    async with httpx.AsyncClient() as client:
        # Fetch all products
        products_response = await client.get(products_url)
        recommendations_response = await client.get(recommendations_url)
        catalogue_response = await client.get(catalogue_url)

    products = products_response.json() if products_response.status_code == 200 else []
    recommendations = recommendations_response.json()[:5] if recommendations_response.status_code == 200 else []
    catalogue = catalogue_response.json() if catalogue_response.status_code == 200 else []

    featured_product = recommendations[0] if recommendations else (products[0] if products else {})
    rec_products = recommendations[1:5] if len(recommendations) > 1 else products[1:5]

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "featured_product": featured_product,
            "rec_products": rec_products,
            "cat_products": catalogue,
            "user_id": DEFAULT_USER_ID,
        },
    )
