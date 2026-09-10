"""Provider-compatible gateway error responses."""

from __future__ import annotations


class GatewayError(Exception):
    """An error that serializes to the provider-compatible error envelope."""

    def __init__(
        self,
        status_code: int,
        message: str,
        error_type: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.body = {"error": {"message": message, "type": error_type, "code": error_type}}
        self.headers = headers or {}
        super().__init__(message)


def gateway_error(status_code: int, message: str, error_type: str) -> GatewayError:
    """Create an error without echoing request content."""
    return GatewayError(status_code, message, error_type)
