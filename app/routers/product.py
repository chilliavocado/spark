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

    # Construct API base URLs
    host = request.client.host
    port = "8000"  # Static port; adjust if your server runs on a different port
    scheme = request.scope["scheme"]
    base_api_url = f"{scheme}://{host}:{port}/api"

    # Define API endpoints
    products_url = f"{base_api_url}/products"
    recommendations_url = f"{base_api_url}/recommendations?user_id={DEFAULT_USER_ID}"
    catalogue_url = f"{base_api_url}/catalogue"

    # Initialize data variables
    products, recommendations, catalogue = [], [], []

    # Asynchronously fetch data from APIs
    async with httpx.AsyncClient() as client:
        # Fetch all products for the catalogue display
        products_response = await client.get(products_url)
        if products_response.status_code == 200:
            products = products_response.json()
        else:
            print("Error fetching products:", products_response.status_code)

        # Fetch top 5 recommended products for the user
        recommendations_response = await client.get(recommendations_url)
        if recommendations_response.status_code == 200:
            recommendations = recommendations_response.json()[:5]  # Limit to 5 recommendations
        else:
            print("Error fetching recommendations:", recommendations_response.status_code)

        # Fetch the full product catalogue (optionally filtered by category in the future)
        catalogue_response = await client.get(catalogue_url)
        if catalogue_response.status_code == 200:
            catalogue = catalogue_response.json()
        else:
            print("Error fetching catalogue:", catalogue_response.status_code)

    # Select featured product and additional recommended products
    featured_product = recommendations[0] if recommendations else (products[0] if products else {})
    rec_products = recommendations[1:5] if len(recommendations) > 1 else products[1:5]

    # Render index template with fetched data
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "featured_product": featured_product,
            "rec_products": rec_products,
            "cat_products": catalogue,
        },
    )


# from fastapi import APIRouter, Request
# from fastapi.responses import HTMLResponse
# from fastapi.templating import Jinja2Templates
# import httpx

# router = APIRouter()
# templates = Jinja2Templates(directory="app/templates")


# @router.get("/product", response_class=HTMLResponse)
# async def product(request: Request, pid: int):
#     products = []  # dummy product data

#     # construct api url dynamically
#     host = request.client.host
#     port = "8000"  # request.client.port not working!
#     scheme = request.scope["scheme"]
#     api_url = f"{scheme}://{host}:{port}/api"

#     async with httpx.AsyncClient() as client:
#         response = await client.get(api_url)
#         if response.status_code == 200:
#             products = response.json()
#         else:
#             print("Error fetching data:", response.status_code)
#             products = [{"ERROR CODE": response.status_code, "Message": response.reason_phrase}]

#     selected_product = products[pid - 1]  # dummy data, to be fetch from recommendation api
#     rec_products = products[1:5]  # dummy data, to be fetch from recommendation api

#     return templates.TemplateResponse("product.html", {"request": request, "selected_product": selected_product, "rec_products": rec_products})
