"""
Resilience utilities for retry logic and circuit breaker pattern.
Provides fault tolerance for LLM requests.
"""

import logging
import time
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    Circuit breaker pattern for handling repeated failures.
    
    States:
    - CLOSED: Normal operation
    - OPEN: Too many failures, rejecting requests
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(self, failure_threshold: int = 3, 
                 recovery_timeout: int = 60,
                 name: str = "CircuitBreaker"):
        """
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            name: Name for logging
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        
        self.failure_count = 0
        self.last_failure_time = None
        self.is_open = False
    
    def call(self, func: Callable, *args, fallback: Any = None, **kwargs) -> Any:
        """
        Execute function through circuit breaker.
        
        Args:
            func: Function to call
            *args/**kwargs: Arguments for function
            fallback: Value to return if circuit is open
        
        Returns:
            Function result or fallback
        """
        
        # Check if circuit should attempt recovery
        if self.is_open:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                logger.info(f"{self.name}: Attempting recovery...")
                self.is_open = False
                self.failure_count = 0
            else:
                logger.warning(f"{self.name}: Circuit OPEN, using fallback")
                return fallback
        
        # Try to execute
        try:
            result = func(*args, **kwargs)
            
            # Reset on success
            if self.failure_count > 0:
                logger.info(f"{self.name}: Success, resetting failure count")
                self.failure_count = 0
            
            return result
        
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            logger.error(f"{self.name}: Failure {self.failure_count}/{self.failure_threshold}: {str(e)}")
            
            # Open circuit if threshold exceeded
            if self.failure_count >= self.failure_threshold:
                self.is_open = True
                logger.warning(f"{self.name}: Circuit OPEN after {self.failure_count} failures")
            
            return fallback


def retry_with_backoff(max_retries: int = 3, 
                       initial_delay: float = 1.0,
                       backoff_factor: float = 2.0,
                       max_delay: float = 60.0):
    """
    Decorator for retry logic with exponential backoff.
    
    Args:
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay on each retry
        max_delay: Maximum delay between retries
    
    Example:
        @retry_with_backoff(max_retries=3)
        def call_llm():
            return query_llm(prompt)
    """
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        logger.info(f"Retry attempt {attempt}/{max_retries} for {func.__name__} after {delay}s delay")
                        time.sleep(delay)
                    
                    return func(*args, **kwargs)
                
                except Exception as e:
                    last_exception = e
                    logger.warning(f"{func.__name__} attempt {attempt + 1} failed: {str(e)}")
                    
                    if attempt < max_retries:
                        delay = min(delay * backoff_factor, max_delay)
            
            logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
            raise last_exception
        
        return wrapper
    return decorator


def retry_simple(max_retries: int = 3, delay: float = 2.0):
    """
    Simple retry decorator with fixed delay.
    
    Args:
        max_retries: Number of retries
        delay: Fixed delay between retries in seconds
    """
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        logger.info(f"Retry {attempt}/{max_retries} for {func.__name__}")
                        time.sleep(delay)
                    
                    return func(*args, **kwargs)
                
                except Exception as e:
                    last_exception = e
                    logger.warning(f"{func.__name__} attempt {attempt + 1} failed")
            
            logger.error(f"Failed after {max_retries + 1} attempts")
            raise last_exception
        
        return wrapper
    return decorator


def with_fallback(fallback_value: Any):
    """
    Decorator that returns fallback value on exception instead of raising.
    
    Args:
        fallback_value: Value to return if function fails
    
    Example:
        @with_fallback([])
        def get_threats():
            return query_llm(...)
    """
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{func.__name__} failed, returning fallback: {str(e)}")
                return fallback_value
        
        return wrapper
    return decorator
