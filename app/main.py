from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from app.routers import index, product, api

app = FastAPI()


# no cache response to prevent stale content
class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


# Add the middleware to your FastAPI application
app.add_middleware(NoCacheMiddleware)


app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# routers to other webpages
app.include_router(index.router)
app.include_router(product.router)
app.include_router(api.router, tags=["api"])
