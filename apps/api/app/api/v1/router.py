from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.chat import router as chat_router
from app.api.v1.endpoints.credits import router as credits_router
from app.api.v1.endpoints.datasets import router as datasets_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.suggestions import router as suggestions_router

# Initialize the main API router for version 1
api_router = APIRouter()

# Register endpoint sub-routers
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(datasets_router, prefix="/datasets", tags=["datasets"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(credits_router, prefix="/credits", tags=["credits"])
# Suggestion routes carry their own full paths (/datasets/.../suggestions,
# /suggestions/...), so they mount without an extra prefix.
api_router.include_router(suggestions_router, tags=["suggestions"])
