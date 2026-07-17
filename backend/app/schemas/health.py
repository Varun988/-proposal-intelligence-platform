from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response returned by the application health endpoint."""

    status: Literal["healthy"]
    application: str
    version: str
    environment: str
