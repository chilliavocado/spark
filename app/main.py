from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routers import index, product, api

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# routers to other webpages
app.include_router(index.router)
app.include_router(product.router)
app.include_router(api.router, tags=["api"])