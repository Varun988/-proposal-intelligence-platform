from app.api.routes.assessments import (
    router as assessments_router,
)
from app.api.routes.health import (
    router as health_router,
)

__all__ = [
    "assessments_router",
    "health_router",
]
