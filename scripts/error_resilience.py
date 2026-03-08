"""Error Resilience Core Module

Provides error handling patterns and utilities for robust agent operations.
Includes retry logic, circuit breaker, pre-flight validation, and error tracking.

Usage:
    from error_resilience import retry_with_backoff, PreflightValidator, ErrorCategory
    
    @retry_with_backoff(max_attempts=3)
    def risky_api_call():
        # Your code here
        pass
"""

from enum import Enum
import time
import random
import logging
from functools import wraps
from typing import Callable, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Classification of error types for intelligent retry decisions."""
    TRANSIENT = "transient"      # Network blip, rate limit - should retry
    PERMANENT = "permanent"       # 404, auth failure - don't retry
    RECOVERABLE = "recoverable"   # Disk full, can be fixed - retry with delay
    FATAL = "fatal"              # Code bug, invalid state - fail immediately


class PreflightError(Exception):
    """Raised when pre-flight validation fails."""
    pass


class TransientError(Exception):
    """Raised for transient errors that should be retried."""
    pass


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open and blocking requests."""
    pass


class PreflightValidator:
    """Pre-flight validation checks before operations.
    
    Validates preconditions to prevent errors before they occur.
    Implements defensive programming pattern.
    """
    
    @staticmethod
    def check_file_readable(path: str) -> None:
        """Validate that a file exists and is readable.
        
        Args:
            path: File path to validate
            
        Raises:
            PreflightError: If validation fails
        """
        import os
        
        checks = [
            (os.path.exists(path), f"File not found: {path}"),
            (os.path.isfile(path), f"Path is not a file: {path}"),
            (os.access(path, os.R_OK), f"No read permission: {path}"),
            (os.path.getsize(path) > 0, f"Empty file: {path}")
        ]
        
        for check, error_msg in checks:
            if not check:
                logger.error(f"Pre-flight check failed: {error_msg}")
                raise PreflightError(error_msg)
    
    @staticmethod
    def check_file_writable(path: str, check_space: bool = True) -> None:
        """Validate that a file path is writable.
        
        Args:
            path: File path to validate
            check_space: Whether to check disk space availability
            
        Raises:
            PreflightError: If validation fails
        """
        import os
        
        directory = os.path.dirname(path) or "."
        
        # Check directory exists or can be created
        if not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created directory: {directory}")
            except Exception as e:
                raise PreflightError(f"Cannot create directory {directory}: {e}")
        
        # Check write permission
        if not os.access(directory, os.W_OK):
            raise PreflightError(f"No write permission in directory: {directory}")
        
        # Check disk space (require at least 10MB free)
        if check_space:
            import shutil
            stat = shutil.disk_usage(directory)
            free_mb = stat.free / (1024 * 1024)
            if free_mb < 10:
                raise PreflightError(f"Insufficient disk space: {free_mb:.1f}MB free")
    
    @staticmethod
    def check_dict_keys(data: dict, required_keys: list) -> None:
        """Validate that a dictionary contains required keys.
        
        Args:
            data: Dictionary to validate
            required_keys: List of required key names
            
        Raises:
            PreflightError: If any required key is missing
        """
        missing = [key for key in required_keys if key not in data]
        if missing:
            raise PreflightError(f"Missing required keys: {missing}")


class RetryStrategy:
    """Retry strategy with exponential backoff and jitter.
    
    Implements AWS SDK retry pattern with exponential backoff and jitter
    to prevent thundering herd problem.
    """
    
    def __init__(self, max_attempts: int = 3, backoff_base: float = 1.0):
        """Initialize retry strategy.
        
        Args:
            max_attempts: Maximum number of retry attempts
            backoff_base: Base delay in seconds for exponential backoff
        """
        self.max_attempts = max_attempts
        self.backoff_base = backoff_base
    
    def execute_with_retry(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with retry logic.
        
        Args:
            operation: Callable to execute
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            Result of operation
            
        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(1, self.max_attempts + 1):
            try:
                logger.info(f"Attempt {attempt}/{self.max_attempts}")
                return operation(*args, **kwargs)
                
            except TransientError as e:
                last_exception = e
                if attempt == self.max_attempts:
                    logger.error(f"All {self.max_attempts} attempts failed")
                    raise
                
                # Exponential backoff with jitter
                sleep_time = (self.backoff_base * (2 ** (attempt - 1))) + random.uniform(0, 1)
                logger.warning(f"Transient error on attempt {attempt}: {e}. Retrying in {sleep_time:.2f}s")
                time.sleep(sleep_time)
                
            except Exception as e:
                # Non-transient errors fail immediately
                logger.error(f"Permanent error, not retrying: {e}")
                raise
        
        # Should not reach here, but just in case
        raise last_exception


class CircuitBreaker:
    """Circuit breaker pattern to prevent cascade failures.
    
    Opens after consecutive failures, preventing further calls
    until a timeout period expires.
    """
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of consecutive failures before opening
            timeout: Seconds to wait before attempting to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half_open
    
    def call(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation through circuit breaker.
        
        Args:
            operation: Callable to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result of operation
            
        Raises:
            CircuitBreakerOpen: If circuit is open
        """
        # Check if circuit should transition from open to half-open
        if self.state == "open":
            if self.last_failure_time and \
               datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout):
                logger.info("Circuit breaker transitioning to half-open")
                self.state = "half_open"
            else:
                raise CircuitBreakerOpen("Circuit breaker is open")
        
        try:
            result = operation(*args, **kwargs)
            
            # Success - reset or close circuit
            if self.state == "half_open":
                logger.info("Circuit breaker closing after successful call")
                self.state = "closed"
            self.failure_count = 0
            return result
            
        except Exception as e:
            # Failure - increment count and maybe open circuit
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.failure_count >= self.failure_threshold:
                logger.error(f"Circuit breaker opening after {self.failure_count} failures")
                self.state = "open"
            
            raise


class ErrorPatternTracker:
    """Track and analyze error patterns over time.
    
    Logs errors and provides metrics for observability.
    """
    
    def __init__(self):
        self.error_log = []
        self.error_counts = defaultdict(int)
    
    def log_error(self, error: Exception, category: ErrorCategory, context: dict = None):
        """Log an error occurrence.
        
        Args:
            error: Exception that occurred
            category: Error category
            context: Additional context information
        """
        error_type = type(error).__name__
        self.error_counts[error_type] += 1
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "category": category.value,
            "message": str(error),
            "context": context or {}
        }
        self.error_log.append(log_entry)
        logger.info(f"Logged error: {error_type} ({category.value})")
    
    def get_error_stats(self) -> dict:
        """Get error statistics.
        
        Returns:
            Dictionary with error counts and recent errors
        """
        return {
            "total_errors": len(self.error_log),
            "error_counts": dict(self.error_counts),
            "recent_errors": self.error_log[-10:]  # Last 10 errors
        }


def retry_with_backoff(max_attempts: int = 3, backoff_base: float = 1.0):
    """Decorator for automatic retry with exponential backoff.
    
    Usage:
        @retry_with_backoff(max_attempts=3)
        def risky_operation():
            # Your code here
            pass
    
    Args:
        max_attempts: Maximum retry attempts
        backoff_base: Base delay for exponential backoff
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            strategy = RetryStrategy(max_attempts, backoff_base)
            return strategy.execute_with_retry(func, *args, **kwargs)
        return wrapper
    return decorator


# Global instances for convenience
error_tracker = ErrorPatternTracker()
default_circuit_breaker = CircuitBreaker()
