"""Custom application exceptions and their FastAPI exception handlers.

This build has no authentication, so there are intentionally no
Unauthorized/Forbidden exception types here — only the domain errors the
video/clip pipeline needs.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base class for all custom application exceptions."""

    def __init__(self, message: str, code: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppException):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str) -> None:
        super().__init__(f"{resource} not found", "NOT_FOUND", status.HTTP_404_NOT_FOUND)


class ConflictError(AppException):
    """Raised when a request conflicts with the current state of a resource."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "CONFLICT", status.HTTP_409_CONFLICT)


class ValidationError(AppException):
    """Raised when request input fails a domain-level validation rule."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "VALIDATION_ERROR", status.HTTP_422_UNPROCESSABLE_CONTENT)


class ProcessingError(AppException):
    """Raised when a step of the video/clip processing pipeline fails.

    Examples: yt-dlp download failure, transcription failure, ffmpeg
    crop/caption-burn failure.
    """

    def __init__(self, message: str, status_code: int = status.HTTP_422_UNPROCESSABLE_CONTENT) -> None:
        super().__init__(message, "PROCESSING_ERROR", status_code)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Convert any AppException subclass into a structured JSON response."""
    logger.warning("AppException handled: code=%s message=%s path=%s", exc.code, exc.message, request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler so unexpected errors never leak a raw traceback."""
    logger.error("Unhandled exception on path=%s: %s", request.url.path, exc, exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Wire all custom exception handlers onto the given FastAPI app instance."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
