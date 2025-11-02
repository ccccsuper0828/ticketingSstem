from fastapi import APIRouter

from app.api.v1 import api_router as v1_router


api_router = APIRouter()

# Versioned APIs
api_router.include_router(v1_router, prefix="/v1")


@api_router.get("/health", tags=["health"])  # Simple health endpoint for readiness checks
def health_check() -> dict:
    return {"status": "ok"}


