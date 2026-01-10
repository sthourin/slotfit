"""
Custom exceptions for SlotFit API
"""
from typing import Optional


class SlotFitException(Exception):
    """Base exception for SlotFit application"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(SlotFitException):
    """Resource not found"""
    def __init__(self, resource: str, identifier: Optional[str] = None):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(message, status_code=404)


class ValidationError(SlotFitException):
    """Validation error"""
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class UnauthorizedError(SlotFitException):
    """Unauthorized access"""
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)


class ForbiddenError(SlotFitException):
    """Forbidden access"""
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403)
