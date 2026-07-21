from fastapi import APIRouter
from app.api.v1.endpoints.health import router as health_router

# Initialize the main API router for version 1
api_router = APIRouter()

# Register endpoint sub-routers
api_router.include_router(health_router, prefix="/health", tags=["health"])

