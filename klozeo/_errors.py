"""Exception classes for the Klozeo SDK."""

from __future__ import annotations


class KlozeoError(Exception):
    """Base exception for all Klozeo API errors.

    Attributes:
        status_code: HTTP status code from the API response.
        message: Human-readable error description.
        code: Machine-readable error code string.
    """

    def __init__(self, message: str, status_code: int = 0, code: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code

    def __repr__(self) -> str:
        return f"{type(self).__name__}(status_code={self.status_code}, code={self.code!r}, message={self.message!r})"


class NotFoundError(KlozeoError):
    """Raised when the requested resource does not exist (HTTP 404)."""

    def __init__(self, message: str = "Resource not found", code: str = "not_found") -> None:
        super().__init__(message, status_code=404, code=code)


class UnauthorizedError(KlozeoError):
    """Raised when the API key is missing or invalid (HTTP 401)."""

    def __init__(self, message: str = "Unauthorized", code: str = "unauthorized") -> None:
        super().__init__(message, status_code=401, code=code)


class ForbiddenError(KlozeoError):
    """Raised when the account limit is reached or access is denied (HTTP 403).

    This typically means the leads limit has been reached and a plan upgrade
    is required.
    """

    def __init__(self, message: str = "Forbidden", code: str = "forbidden") -> None:
        super().__init__(message, status_code=403, code=code)


class RateLimitedError(KlozeoError):
    """Raised when the rate limit is exceeded (HTTP 429).

    Attributes:
        retry_after: Number of seconds to wait before retrying.
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        code: str = "rate_limit_exceeded",
        retry_after: float = 0.0,
    ) -> None:
        super().__init__(message, status_code=429, code=code)
        self.retry_after = retry_after


class BadRequestError(KlozeoError):
    """Raised when the request body or parameters are invalid (HTTP 400)."""

    def __init__(self, message: str = "Bad request", code: str = "bad_request") -> None:
        super().__init__(message, status_code=400, code=code)


class ValidationError(KlozeoError):
    """Raised client-side before any HTTP call when input validation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=0, code="validation_error")
