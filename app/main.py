from fastapi import FastAPI
from app.core.config import settings

# We pass the validated project name configuration directly into the FastAPI instance
app = FastAPI(title=settings.PROJECT_NAME)


@app.get("/")
def read_root():
    # Return verification data so we can check it in the browser
    return {
        "message": "Hello from Visual AI Analyst",
        "project_name": settings.PROJECT_NAME,
        "environment": settings.ENV,
    }
