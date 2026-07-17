from app.api.routes.assessments import (
    router as assessments_router,
)
from app.api.routes.documents import (
    router as documents_router,
)
from app.api.routes.health import (
    router as health_router,
)

__all__ = [
    "assessments_router",
    "documents_router",
    "health_router",
]