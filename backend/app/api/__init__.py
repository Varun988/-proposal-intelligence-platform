from fastapi import APIRouter

from app.api.routes import (
    assessments_router,
    health_router,
)


api_router = APIRouter()

api_router.include_router(
    health_router,
)
api_router.include_router(
    assessments_router,
)


__all__ = [
    "api_router",
]
