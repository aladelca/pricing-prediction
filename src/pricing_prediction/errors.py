from __future__ import annotations


class ApiError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundError(ApiError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 404)


class DomainValidationError(ApiError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 422)
