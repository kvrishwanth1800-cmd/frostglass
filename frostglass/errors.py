"""Provider-compatible gateway error responses."""

from __future__ import annotations

from fastapi import HTTPException


def gateway_error(status_code: int, message: str, error_type: str) -> HTTPException:
    """Create an OpenAI-compatible error envelope without request content."""
    return HTTPException(
        status_code=status_code,
        detail={"error": {"message": message, "type": error_type, "code": error_type}},
    )
