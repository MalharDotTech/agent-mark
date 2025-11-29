"""Token management for Meta API with round-robin rotation and cooldown tracking."""

import time
import threading
from typing import List, Dict, Tuple, Optional

from .logging import get_logger
from .exceptions import TokenException

logger = get_logger(__name__)


class TokenManager:
    """
    Manages multiple Meta access tokens with round-robin rotation and cooldown tracking.
    
    Based on the working Python script's TokenPool implementation, this class provides:
    - Round-robin token distribution
    - Cooldown tracking for rate-limited tokens
    - Thread-safe operations using threading locks
    """
    
    def __init__(self, tokens: List[str]):
        """
        Initialize TokenManager with a list of access tokens.
        
        Args:
            tokens: List of Meta API access tokens
        """
        if not tokens:
            raise TokenException("At least one access token must be provided")
        
        self.tokens = list(tokens)
        self.cooldowns: Dict[int, float] = {}  # token_index -> epoch_time_allowed
        self.lock = threading.Lock()
        self.ptr = 0  # Round-robin pointer
        
        logger.info(f"TokenManager initialized with {len(self.tokens)} tokens")
    
    def get_available_token(self) -> Tuple[int, str]:
        """
        Get an available token using round-robin rotation.
        
        Returns:
            Tuple of (token_index, token_string)
            
        If all tokens are in cooldown, waits for the token with shortest cooldown.
        """
        with self.lock:
            n = len(self.tokens)
            current_time = time.time()
            
            # Try to find an available token using round-robin
            for _ in range(n):
                i = self.ptr
                self.ptr = (self.ptr + 1) % n
                
                if current_time >= self.cooldowns.get(i, 0.0):
                    logger.debug(f"Using token {i} (round-robin)")
                    return i, self.tokens[i]
            
            # All tokens are in cooldown, wait for the one with shortest cooldown
            i = min(self.cooldowns, key=self.cooldowns.get, default=0)
            wait_time = max(0.0, self.cooldowns.get(i, 0.0) - current_time)
            
            if wait_time > 0:
                logger.warning(f"All tokens in cooldown, waiting {wait_time:.1f}s for token {i}")
                time.sleep(wait_time)
            
            return i, self.tokens[i]
    
    async def get_available_token_async(self) -> Tuple[int, str]:
        """
        Async version of get_available_token for use in async contexts.
        
        Returns:
            Tuple of (token_index, token_string)
        """
        import asyncio
        
        with self.lock:
            n = len(self.tokens)
            current_time = time.time()
            
            # Try to find an available token using round-robin
            for _ in range(n):
                i = self.ptr
                self.ptr = (self.ptr + 1) % n
                
                if current_time >= self.cooldowns.get(i, 0.0):
                    logger.debug(f"Using token {i} (round-robin)")
                    return i, self.tokens[i]
            
            # All tokens are in cooldown, wait for the one with shortest cooldown
            i = min(self.cooldowns, key=self.cooldowns.get, default=0)
            wait_time = max(0.0, self.cooldowns.get(i, 0.0) - current_time)
            
            if wait_time > 0:
                logger.warning(f"All tokens in cooldown, waiting {wait_time:.1f}s for token {i}")
        
        # Wait outside the lock using async sleep
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        return i, self.tokens[i]
    
    def report_rate_limit(self, token_index: int, cooldown_seconds: float) -> None:
        """
        Report that a token has hit a rate limit and should be cooled down.
        
        Args:
            token_index: Index of the token that hit rate limit
            cooldown_seconds: Number of seconds to cool down the token
        """
        with self.lock:
            cooldown_until = time.time() + max(1.0, cooldown_seconds)
            self.cooldowns[token_index] = cooldown_until
            
            logger.warning(f"Token {token_index} cooled down for {cooldown_seconds}s "
                          f"(until {time.strftime('%H:%M:%S', time.localtime(cooldown_until))})")
    
    def is_token_available(self, token_index: int) -> bool:
        """
        Check if a specific token is available (not in cooldown).
        
        Args:
            token_index: Index of the token to check
            
        Returns:
            True if token is available, False if in cooldown
        """
        with self.lock:
            current_time = time.time()
            return current_time >= self.cooldowns.get(token_index, 0.0)
    
    def get_token_stats(self) -> Dict[str, any]:
        """
        Get statistics about token usage and cooldowns.
        
        Returns:
            Dictionary with token statistics
        """
        with self.lock:
            current_time = time.time()
            available_count = 0
            cooldown_info = {}
            
            for i in range(len(self.tokens)):
                cooldown_until = self.cooldowns.get(i, 0.0)
                if current_time >= cooldown_until:
                    available_count += 1
                    cooldown_info[f"token_{i}"] = "available"
                else:
                    remaining = cooldown_until - current_time
                    cooldown_info[f"token_{i}"] = f"cooldown_{remaining:.1f}s"
            
            return {
                "total_tokens": len(self.tokens),
                "available_tokens": available_count,
                "cooldown_tokens": len(self.tokens) - available_count,
                "current_pointer": self.ptr,
                "token_status": cooldown_info
            }