"""Rate limiting with exponential backoff for Meta API."""

import time
import random
from typing import Dict, Any, Optional, Callable

from .logging import get_logger
from .token_manager import TokenManager
from .exceptions import RateLimitException

logger = get_logger(__name__)


class RateLimiter:
    """
    Handles Meta API rate limiting with exponential backoff and jitter.
    
    Based on the working Python script's rate limiting logic, this class provides:
    - Exponential backoff with jitter for retries
    - Meta API error code handling (4, 17, 32, 613)
    - Token cooldown management when rate limits are hit
    """
    
    # Meta API rate limit error codes and their cooldown periods
    META_ERROR_CODES = {
        4: {"cooldown": 25, "description": "Application request limit"},
        17: {"cooldown": 12, "description": "User request limit"}, 
        32: {"cooldown": 20, "description": "Page request limit"},
        613: {"cooldown": 25, "description": "Rate limit exceeded"}
    }
    
    def __init__(self, token_manager: TokenManager, base_backoff: float = 0.8, max_retries: int = 7):
        """
        Initialize RateLimiter.
        
        Args:
            token_manager: TokenManager instance for handling token cooldowns
            base_backoff: Base backoff time in seconds
            max_retries: Maximum number of retry attempts
        """
        self.token_manager = token_manager
        self.base_backoff = base_backoff
        self.max_retries = max_retries
        
        logger.info(f"RateLimiter initialized with base_backoff={base_backoff}s, max_retries={max_retries}")
    
    def calculate_backoff(self, attempt: int, error_code: Optional[int] = None) -> float:
        """
        Calculate backoff time with exponential increase and jitter.
        
        Args:
            attempt: Current attempt number (0-based)
            error_code: Optional Meta API error code for specific handling
            
        Returns:
            Backoff time in seconds
        """
        # Exponential backoff: base * (2^attempt)
        backoff_time = self.base_backoff * (2 ** attempt)
        
        # Add random jitter (0 to base_backoff seconds)
        jitter = random.uniform(0, self.base_backoff)
        
        total_backoff = backoff_time + jitter
        
        logger.debug(f"Calculated backoff: {total_backoff:.2f}s (attempt={attempt}, "
                    f"base={backoff_time:.2f}s, jitter={jitter:.2f}s)")
        
        return total_backoff
    
    def handle_rate_limit_error(self, error_data: Dict[str, Any], token_index: int) -> None:
        """
        Handle Meta API rate limit error by cooling down the token.
        
        Args:
            error_data: Error response from Meta API
            token_index: Index of the token that received the error
        """
        error_code = error_data.get("code")
        error_subcode = error_data.get("error_subcode")
        message = error_data.get("message", "")
        
        if error_code in self.META_ERROR_CODES:
            error_info = self.META_ERROR_CODES[error_code]
            cooldown_seconds = error_info["cooldown"]
            description = error_info["description"]
            
            logger.warning(f"Rate limit hit - Code: {error_code}, Subcode: {error_subcode}, "
                          f"Description: {description}, Message: {message}")
            
            # Cool down the token
            self.token_manager.report_rate_limit(token_index, cooldown_seconds)
        else:
            logger.error(f"Unhandled Meta API error - Code: {error_code}, Subcode: {error_subcode}, "
                        f"Message: {message}")
    
    def should_retry_error(self, error_data: Dict[str, Any]) -> bool:
        """
        Determine if an error should be retried.
        
        Args:
            error_data: Error response from Meta API
            
        Returns:
            True if the error should be retried, False otherwise
        """
        error_code = error_data.get("code")
        
        # Retry rate limit errors
        if error_code in self.META_ERROR_CODES:
            return True
        
        # Don't retry other errors (authentication, permissions, etc.)
        return False
    
    async def execute_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with exponential backoff retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function call
            
        Raises:
            Exception: If all retry attempts are exhausted
        """
        import asyncio
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Check if function is async
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(f"Function succeeded on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if this is the last attempt
                if attempt >= self.max_retries:
                    logger.error(f"Max retries ({self.max_retries}) exceeded for function {getattr(func, '__name__', 'unknown')}")
                    break
                
                # Calculate and apply backoff
                backoff_time = self.calculate_backoff(attempt)
                logger.warning(f"Function {getattr(func, '__name__', 'unknown')} failed on attempt {attempt + 1}, "
                              f"retrying in {backoff_time:.2f}s: {str(e)}")
                
                await asyncio.sleep(backoff_time)
        
        # All retries exhausted, raise the last exception
        raise last_exception
    
    def backoff_sleep(self, attempt: int) -> None:
        """
        Sleep for the calculated backoff time.
        
        Args:
            attempt: Current attempt number (0-based)
        """
        backoff_time = self.calculate_backoff(attempt)
        logger.debug(f"Sleeping for {backoff_time:.2f}s (attempt {attempt})")
        time.sleep(backoff_time)