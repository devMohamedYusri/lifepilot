"""Custom exception classes for consistent error handling."""
from typing import Optional, Any, Dict


class LifePilotException(Exception):
    """Base exception for all LifePilot errors."""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = 500, 
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response."""
        result = {
            "error": self.__class__.__name__,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


class NotFoundError(LifePilotException):
    """Resource not found error."""
    
    def __init__(self, resource: str, resource_id: Any):
        super().__init__(
            message=f"{resource} with ID {resource_id} not found",
            status_code=404,
            details={"resource": resource, "id": resource_id}
        )


class ValidationError(LifePilotException):
    """Request validation error."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        details = {"field": field} if field else {}
        super().__init__(
            message=message,
            status_code=400,
            details=details
        )


class ExternalServiceError(LifePilotException):
    """Error from external service (e.g., Groq API)."""
    
    def __init__(self, service: str, message: str, original_error: Optional[str] = None):
        super().__init__(
            message=f"{service} service error: {message}",
            status_code=503,
            details={"service": service, "original_error": original_error}
        )


class DatabaseError(LifePilotException):
    """Database operation error."""
    
    def __init__(self, operation: str, message: str):
        super().__init__(
            message=f"Database {operation} failed: {message}",
            status_code=500,
            details={"operation": operation}
        )


class RateLimitError(LifePilotException):
    """Rate limit exceeded error."""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Rate limit exceeded. Please try again later.",
            status_code=429,
            details={"retry_after_seconds": retry_after}
        )


class AuthenticationError(LifePilotException):
    """Authentication failed error."""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=401
        )


class AIServiceError(ExternalServiceError):
    """Specific error for AI service failures."""
    
    def __init__(
        self, 
        message: str, 
        provider: str = "groq", 
        code: str = "ai_error",
        status_code: int = 503
    ):
        super().__init__(
            service=provider,
            message=message,
        )
        self.code = code
        self.status_code = status_code
        self.details["code"] = code

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["code"] = self.code
        return result
