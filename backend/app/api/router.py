from fastapi import APIRouter

from app.api.routes import alerts, auth, dashboard, data_query, devices, farms, inspections, notifications, protocol, sensors, sheds, telemetry

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(farms.router)
api_router.include_router(sheds.router)
api_router.include_router(devices.router)
api_router.include_router(sensors.router)
api_router.include_router(telemetry.router)
api_router.include_router(alerts.router)
api_router.include_router(inspections.router)
api_router.include_router(protocol.router)
api_router.include_router(data_query.router)
api_router.include_router(notifications.router)
