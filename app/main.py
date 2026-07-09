from fastapi import FastAPI
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import logger

# Initialize application
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Register the main version 1 router
# All endpoints registered inside api_router will automatically get the "/api/v1" prefix.
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.on_event("startup")
async def startup_event():
    # Log that the app is ready using our configured logger
    logger.info("Application starting up in %s environment...", settings.ENV)


@app.get("/")
def read_root():
    # Log incoming request
    logger.debug("Root path '/' accessed")
    return {
        "message": "Hello from Visual AI Analyst",
        "project_name": settings.PROJECT_NAME,
    }

