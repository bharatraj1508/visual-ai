from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.chat import router as chat_router
from app.api.v1.endpoints.datasets import router as datasets_router
from app.api.v1.endpoints.health import router as health_router

# Initialize the main API router for version 1
api_router = APIRouter()

# Register endpoint sub-routers
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(datasets_router, prefix="/datasets", tags=["datasets"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
