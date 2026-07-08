from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings


app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(api_router)


@app.get("/health", tags=["system"])
def health_check() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
    }
