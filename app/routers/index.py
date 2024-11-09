# index.py

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

DEFAULT_USER_ID = 0


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Fetches products and recommendations data for the homepage."""

    base_url = request.base_url
    base_api_url = f"{base_url}api"

    user_id = DEFAULT_USER_ID  # Default value in case of failure
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:  # Set a 5-second timeout
            user_id_response = await client.get(f"{base_api_url}/currentUser")
            if user_id_response.status_code == 200:
                user_id = user_id_response.json().get("user_id", DEFAULT_USER_ID)
            else:
                raise HTTPException(status_code=user_id_response.status_code, detail="Error fetching user ID")
    except httpx.ReadTimeout:
        print("Timeout while fetching user ID.")
    except Exception as e:
        print(f"Error while fetching user ID: {e}")

    # Append user_id to the recommendations URL
    recommendations_url = f"{base_api_url}/recommendations?user_id={user_id}"

    async with httpx.AsyncClient() as client:
        try:
            # Fetch all products and data
            products_response = await client.get(f"{base_api_url}/products")
            recommendations_response = await client.get(recommendations_url)
            catalogue_response = await client.get(f"{base_api_url}/catalogue")
        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred: {e}")
            products_response, recommendations_response, catalogue_response = None, None, None
        except httpx.RequestError as e:
            print(f"Request error: {e}")
            products_response, recommendations_response, catalogue_response = None, None, None

    # Process responses and pass user_id to the template
    products = products_response.json() if products_response and products_response.status_code == 200 else []
    recommendations = recommendations_response.json()[:5] if recommendations_response and recommendations_response.status_code == 200 else []
    catalogue = catalogue_response.json() if catalogue_response and catalogue_response.status_code == 200 else []

    featured_product = recommendations[0] if recommendations else (products[0] if products else {})
    rec_products = recommendations[1:5] if len(recommendations) > 1 else products[1:5]

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "featured_product": featured_product,
            "rec_products": rec_products,
            "cat_products": catalogue,
            "user_id": user_id,
        },
    )
