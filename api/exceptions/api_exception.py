"""API exception module."""
from fastapi import HTTPException, status


class APIException(HTTPException):
    """Base API exception class."""

    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "An unexpected error occurred",
    ):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundError(APIException):
    """Resource not found exception."""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class BadRequestError(APIException):
    """Bad request exception."""

    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class InsufficientDataError(APIException):
    """Insufficient data for calculation exception."""

    def __init__(self, detail: str = "Insufficient data for calculation"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)
