from fastapi import APIRouter

# Initialize the main API router for version 1
api_router = APIRouter()

# In the future, we will include specific feature routers like this:
# api_router.include_router(dataset_router, prefix="/datasets", tags=["datasets"])
