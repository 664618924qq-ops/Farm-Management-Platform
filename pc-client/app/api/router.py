from fastapi import APIRouter

from app.api.routes import devices, platform, sites, telemetry


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(sites.router, prefix="/sites", tags=["sites"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(telemetry.router, prefix="/telemetry", tags=["telemetry"])
api_router.include_router(platform.router, prefix="/platform", tags=["platform"])
