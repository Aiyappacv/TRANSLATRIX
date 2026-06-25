"""
FastAPI Middleware
Request ID tracking, tenant context, logging, and error handling
"""
import time
import uuid
import structlog
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.core.tenant_context import set_current_tenant_id, clear_current_tenant_id
from app.exceptions import TranslatrixException, http_exception_from_app_exception

logger = structlog.get_logger()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Add unique request ID to each request
    Tracks request ID in logs and response headers
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Store in request state
        request.state.request_id = request_id

        # Add to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Manage tenant context for multi-tenancy
    Sets tenant ID from authenticated user context
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Clear any existing tenant context
        clear_current_tenant_id()

        try:
            # Process request (tenant ID will be set by auth dependency)
            response = await call_next(request)
            return response
        finally:
            # Always clear tenant context after request
            clear_current_tenant_id()


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all requests and responses with timing information
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Log incoming request
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
        )

        try:
            response = await call_next(request)

            # Calculate request duration
            duration = time.time() - start_time

            # Log successful response
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_seconds=round(duration, 3),
            )

            return response

        except Exception as exc:
            # Calculate request duration
            duration = time.time() - start_time

            # Log error
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                error=str(exc),
                error_type=type(exc).__name__,
                duration_seconds=round(duration, 3),
            )
            raise


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware
    Converts application exceptions to HTTP responses
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except TranslatrixException as exc:
            # Convert application exception to HTTP exception
            http_exc = http_exception_from_app_exception(exc)

            # Log the error
            logger.error(
                "application_error",
                error_type=type(exc).__name__,
                error_message=exc.message,
                error_details=exc.details,
                path=request.url.path,
            )

            # Return error response
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=http_exc.status_code,
                content=http_exc.detail,
            )
        except Exception as exc:
            # Unexpected error
            logger.exception(
                "unexpected_error",
                error_type=type(exc).__name__,
                error_message=str(exc),
                path=request.url.path,
            )

            # Return generic error response
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=500,
                content={
                    "message": "Internal server error",
                    "details": {}
                },
            )


def setup_middleware(app: ASGIApp) -> None:
    """
    Setup all middleware for the application

    Args:
        app: FastAPI application instance
    """
    # Add middleware in reverse order (last added is first executed)
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(RequestIDMiddleware)
