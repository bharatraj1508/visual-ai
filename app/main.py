from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import logger

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Log that the app is starting up
    logger.info("Application starting up in %s environment...", settings.ENV)
    yield
    # Log that the app is shutting down
    logger.info("Application shutting down...")


# Initialize application
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Allow the Next.js frontend to call the API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register the main version 1 router
app.include_router(api_router, prefix=settings.API_V1_STR)



@app.get("/")
def read_root():
    # Log incoming request
    logger.debug("Root path '/' accessed")
    return {
        "message": "Hello from Visual AI Analyst",
        "project_name": settings.PROJECT_NAME,
    }

