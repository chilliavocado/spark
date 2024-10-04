
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/product", response_class=HTMLResponse)
async def read_products():
    return templates.TemplateResponse("product.html")
