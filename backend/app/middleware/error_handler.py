"""
Centralized error handling middleware
"""
import logging
from typing import Callable
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import SlotFitException
from app.core.logging import get_logger

logger = get_logger(__name__)


async def error_handler_middleware(request: Request, call_next: Callable):
    """
    Global error handler middleware.
    
    Catches all exceptions and returns consistent error responses.
    """
    try:
        response = await call_next(request)
        return response
    except SlotFitException as e:
        # Custom application exceptions
        logger.warning(
            f"Application error: {e.message}",
            extra={"status_code": e.status_code, "path": request.url.path}
        )
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.message}
        )
    except StarletteHTTPException as e:
        # FastAPI HTTP exceptions
        logger.warning(
            f"HTTP error: {e.detail}",
            extra={"status_code": e.status_code, "path": request.url.path}
        )
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail}
        )
    except RequestValidationError as e:
        # Pydantic validation errors
        logger.warning(
            f"Validation error: {str(e)}",
            extra={"path": request.url.path, "errors": e.errors()}
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": e.errors()}
        )
    except Exception as e:
        # Unexpected errors - log full traceback
        logger.error(
            f"Unexpected error: {str(e)}",
            exc_info=True,
            extra={"path": request.url.path, "method": request.method}
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error" if not logger.isEnabledFor(logging.DEBUG) else str(e)
            }
        )
