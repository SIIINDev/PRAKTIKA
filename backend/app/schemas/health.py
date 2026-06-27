"""Pydantic schema for the health endpoint."""

from pydantic import BaseModel


class HealthOut(BaseModel):
    """Aggregated readiness of the service and its dependencies."""

    status: str
    elasticsearch: str
    redis: str
    postgres: str
