from fastapi import FastAPI
from app.api.v1.router import api_router
from app.core.config import settings

# Initialize application
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Register the main version 1 router
# All endpoints registered inside api_router will automatically get the "/api/v1" prefix.
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def read_root():
    return {
        "message": "Hello from Visual AI Analyst",
        "project_name": settings.PROJECT_NAME,
    }
