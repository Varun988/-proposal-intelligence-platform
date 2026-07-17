from fastapi import FastAPI

from app.api import api_router
from app.core.config import get_settings
from app.core.logging import (
    configure_logging,
    get_logger,
)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()

    configure_logging(
        log_level=settings.log_level,
        json_format=settings.log_json_format,
    )

    logger = get_logger(__name__)

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        description=(
            "Backend API for AI-assisted proposal analysis "
            "and vendor risk evaluation."
        ),
    )

    application.include_router(
        api_router,
        prefix=settings.api_v1_prefix,
    )

    logger.info(
        "Application configured",
        extra={
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "environment": settings.app_env,
        },
    )

    return application


app = create_app()