"""
Custom exception classes and FastAPI exception handlers.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


# ── Custom Exceptions ────────────────────────────────────────────────────

class FinSightException(Exception):
    """Base exception for all FinSight business errors."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class TallyConnectionError(FinSightException):
    """Raised when unable to connect to Tally Prime."""

    def __init__(self, host: str, port: int, detail: str = ""):
        message = f"Cannot connect to Tally at {host}:{port}"
        if detail:
            message += f" — {detail}"
        super().__init__(message, status_code=502)


class TallyDataError(FinSightException):
    """Raised when Tally returns unexpected or unparseable data."""

    def __init__(self, detail: str):
        super().__init__(f"Tally data error: {detail}", status_code=422)


class SyncInProgressError(FinSightException):
    """Raised when a sync is already running for a client."""

    def __init__(self, client_id: str):
        super().__init__(
            f"A sync job is already running for client {client_id}",
            status_code=409,
        )


class ClientNotFoundError(FinSightException):
    """Raised when a Tally client is not found."""

    def __init__(self, client_id: str):
        super().__init__(
            f"Client {client_id} not found",
            status_code=404,
        )


class NoSyncDataError(FinSightException):
    """Raised when an operation requires synced data that doesn't exist yet."""

    def __init__(self, client_id: str):
        super().__init__(
            f"No synced data found for client {client_id}. Run a Tally sync first.",
            status_code=412,
        )


class ReportGenerationError(FinSightException):
    """Raised when report generation fails."""

    def __init__(self, detail: str):
        super().__init__(f"Report generation failed: {detail}", status_code=500)


# ── Exception Handlers ───────────────────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers with the FastAPI app."""

    @app.exception_handler(FinSightException)
    async def finsight_exception_handler(
        request: Request, exc: FinSightException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": type(exc).__name__,
                "message": exc.message,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred. Please try again.",
            },
        )
