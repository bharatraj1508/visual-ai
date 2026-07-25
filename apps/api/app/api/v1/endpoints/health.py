from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger

router = APIRouter()


@router.get("", status_code=status.HTTP_200_OK)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint to verify backend service and database connectivity."""
    try:
        # Perform a quick database verification query
        await db.execute(text("SELECT 1"))
        logger.debug("Health check database query succeeded.")
        return {
            "status": "healthy",
            "database": "connected",
        }
    except Exception as e:
        logger.error("Health check failed: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed",
        )
