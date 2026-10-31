"""
Shared response schemas used across all routers.
"""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """
    Standard error body returned by all HTTP 4xx / 5xx responses.
    Matches FastAPI's default HTTPException shape so clients can
    always parse error.response.data.detail.
    """

    detail: str
