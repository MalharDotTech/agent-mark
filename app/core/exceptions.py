"""Custom exceptions for Meta API Service."""

from typing import Dict, Any, Optional
from datetime import datetime


class MetaAPIException(Exception):
    """Base exception for Meta API Service errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize MetaAPIException.
        
        Args:
            message: Error message
            error_code: Optional error code
            details: Optional additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "META_API_ERROR"
        self.details = details or {}
        self.timestamp = datetime.utcnow()


class RateLimitException(MetaAPIException):
    """Exception raised when Meta API rate limits are exceeded."""
    
    def __init__(self, message: str, meta_error_code: Optional[int] = None, cooldown_seconds: Optional[int] = None):
        """
        Initialize RateLimitException.
        
        Args:
            message: Error message
            meta_error_code: Meta API error code (4, 17, 32, 613)
            cooldown_seconds: Recommended cooldown period
        """
        super().__init__(message, "RATE_LIMIT_EXCEEDED")
        self.meta_error_code = meta_error_code
        self.cooldown_seconds = cooldown_seconds


class TokenException(MetaAPIException):
    """Exception raised when there are issues with access tokens."""
    
    def __init__(self, message: str, token_index: Optional[int] = None):
        """
        Initialize TokenException.
        
        Args:
            message: Error message
            token_index: Index of the problematic token
        """
        super().__init__(message, "TOKEN_ERROR")
        self.token_index = token_index


class DataExtractionException(MetaAPIException):
    """Exception raised during data extraction operations."""
    
    def __init__(self, message: str, account_id: Optional[str] = None, job_id: Optional[str] = None):
        """
        Initialize DataExtractionException.
        
        Args:
            message: Error message
            account_id: Meta ad account ID where error occurred
            job_id: Job ID where error occurred
        """
        super().__init__(message, "DATA_EXTRACTION_ERROR")
        self.account_id = account_id
        self.job_id = job_id


class ValidationException(MetaAPIException):
    """Exception raised for request validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        """
        Initialize ValidationException.
        
        Args:
            message: Error message
            field: Field name that failed validation
        """
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field


class ConfigurationException(MetaAPIException):
    """Exception raised for configuration errors."""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        """
        Initialize ConfigurationException.
        
        Args:
            message: Error message
            config_key: Configuration key that caused the error
        """
        super().__init__(message, "CONFIGURATION_ERROR")
        self.config_key = config_key