# product.py

from fastapi import APIRouter, Request, HTTPException
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

    # Construct URLs for product details and recommendations
    product_url = f"{base_api_url}/product?product_id={product_id}"
    recommendations_url = f"{base_api_url}/recommendations?user_id={user_id}"

    async with httpx.AsyncClient() as client:
        try:
            # Fetch product details
            product_response = await client.get(product_url)
            # Fetch recommendations
            recommendations_response = await client.get(recommendations_url)
        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred: {e}")
            return JSONResponse(content={"error": "An error occurred while fetching data"}, status_code=500)
        except httpx.RequestError as e:
            print(f"Request error: {e}")
            return JSONResponse(content={"error": "A request error occurred"}, status_code=500)

    # Process responses and pass user_id to the template
    if product_response and product_response.status_code == 200:
        selected_product = product_response.json()
        rec_products = recommendations_response.json()[:5] if recommendations_response and recommendations_response.status_code == 200 else []

        return templates.TemplateResponse(
            "product.html",
            {
                "request": request,
                "selected_product": selected_product,
                "rec_products": rec_products,
                "user_id": user_id,
            },
        )
    else:
        return JSONResponse(content={"error": "Product not found"}, status_code=404)
