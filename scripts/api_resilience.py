"""API Resilience Module

Provides resilient HTTP client wrappers with circuit breaker, retry logic,
rate limiting, and concrete implementations for Trello and Pipedream APIs.
Integrates with error_resilience module for robust error handling.

Usage:
    from api_resilience import TrelloApiClient, PipedreamApiClient
    
    # Trello API with automatic resilience
    trello = TrelloApiClient(api_key='...', token='...')
    card = trello.get_card('board_id', 'card_id')
    
    # Pipedream API with rate limiting
    pipedream = PipedreamApiClient(api_key='...')
    result = pipedream.trigger_workflow('workflow_id', {'data': 'value'})
"""

import time
import requests
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
from collections import deque
import logging

# Import from Module 1
from error_resilience import (
    CircuitBreaker,
    RetryStrategy,
    ErrorCategory,
    TransientError,
    CircuitBreakerOpen,
    error_tracker
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RateLimitHandler:
    """Rate limiting handler with token bucket algorithm.
    
    Implements token bucket algorithm to prevent API rate limit violations.
    Detects 429 responses and respects Retry-After headers.
    
    Attributes:
        requests_per_second: Maximum requests allowed per second
        bucket_size: Maximum burst capacity
        tokens: Current token count
        last_refill: Last token refill timestamp
    """
    
    def __init__(self, requests_per_second: float = 10.0, bucket_size: Optional[int] = None):
        """Initialize rate limit handler.
        
        Args:
            requests_per_second: Rate limit in requests per second
            bucket_size: Bucket capacity (defaults to 2x rate if not specified)
        """
        self.requests_per_second = requests_per_second
        self.bucket_size = bucket_size or int(requests_per_second * 2)
        self.tokens = float(self.bucket_size)
        self.last_refill = time.time()
        logger.info(f"RateLimitHandler initialized: {requests_per_second} req/s, bucket={self.bucket_size}")
    
    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time since last refill."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on elapsed time
        new_tokens = elapsed * self.requests_per_second
        self.tokens = min(self.bucket_size, self.tokens + new_tokens)
        self.last_refill = now
    
    def acquire(self, tokens: int = 1, timeout: float = 30.0) -> bool:
        """Acquire tokens, blocking if necessary.
        
        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum time to wait in seconds
        
        Returns:
            True if tokens acquired, False if timeout
        """
        start_time = time.time()
        
        while True:
            self._refill_tokens()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                logger.warning(f"Rate limit acquire timeout after {elapsed:.1f}s")
                return False
            
            # Wait before retrying
            wait_time = min(0.1, timeout - elapsed)
            time.sleep(wait_time)
    
    def handle_429_response(self, response: requests.Response) -> None:
        """Handle 429 Too Many Requests response.
        
        Args:
            response: HTTP response with 429 status
        """
        retry_after = response.headers.get('Retry-After')
        
        if retry_after:
            try:
                # Retry-After can be seconds or HTTP date
                wait_seconds = int(retry_after)
            except ValueError:
                # Try parsing as HTTP date
                from email.utils import parsedate_to_datetime
                retry_time = parsedate_to_datetime(retry_after)
                wait_seconds = (retry_time - datetime.now()).total_seconds()
            
            logger.warning(f"Rate limited (429), waiting {wait_seconds}s as per Retry-After header")
            time.sleep(max(0, wait_seconds))
        else:
            # Default backoff if no Retry-After header
            logger.warning("Rate limited (429), applying default 60s backoff")
            time.sleep(60)


class ResilientApiClient:
    """Resilient HTTP client with circuit breaker and retry logic.
    
    Wraps HTTP requests with automatic retry, circuit breaker pattern,
    and rate limiting. Base class for specific API clients.
    
    Attributes:
        circuit_breaker: CircuitBreaker instance to prevent cascade failures
        retry_strategy: RetryStrategy for transient error handling
        rate_limiter: RateLimitHandler for rate limiting
        session: Requests session for connection pooling
    """
    
    def __init__(
        self,
        base_url: str,
        requests_per_second: float = 10.0,
        max_retries: int = 3,
        circuit_breaker_threshold: int = 5
    ):
        """Initialize resilient API client.
        
        Args:
            base_url: Base URL for API endpoints
            requests_per_second: Rate limit
            max_retries: Maximum retry attempts
            circuit_breaker_threshold: Failures before circuit opens
        """
        self.base_url = base_url.rstrip('/')
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_breaker_threshold,
            timeout=60
        )
        self.retry_strategy = RetryStrategy(max_attempts=max_retries)
        self.rate_limiter = RateLimitHandler(requests_per_second=requests_per_second)
        self.session = requests.Session()
        logger.info(f"ResilientApiClient initialized for {base_url}")
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> requests.Response:
        """Make HTTP request with resilience patterns.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for requests
        
        Returns:
            HTTP response
        
        Raises:
            TransientError: For retryable errors
            Exception: For permanent errors
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        def _request_impl():
            # Acquire rate limit token
            if not self.rate_limiter.acquire(timeout=30.0):
                raise TransientError("Rate limit acquire timeout")
            
            try:
                response = self.session.request(method, url, **kwargs)
                
                # Handle rate limiting
                if response.status_code == 429:
                    self.rate_limiter.handle_429_response(response)
                    raise TransientError("Rate limited (429)")
                
                # Handle server errors (retryable)
                if response.status_code >= 500:
                    error_msg = f"Server error {response.status_code}: {response.text[:200]}"
                    logger.warning(error_msg)
                    raise TransientError(error_msg)
                
                # Handle client errors (not retryable)
                if response.status_code >= 400:
                    error_msg = f"Client error {response.status_code}: {response.text[:200]}"
                    logger.error(error_msg)
                    error_tracker.log_error(
                        Exception(error_msg),
                        ErrorCategory.PERMANENT,
                        {'url': url, 'method': method}
                    )
                    raise Exception(error_msg)
                
                return response
                
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection error: {e}")
                raise TransientError(f"Connection error: {e}")
            
            except requests.exceptions.Timeout as e:
                logger.warning(f"Request timeout: {e}")
                raise TransientError(f"Timeout: {e}")
        
        # Apply circuit breaker and retry
        return self.circuit_breaker.call(
            self.retry_strategy.execute_with_retry,
            _request_impl
        )
    
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """Make GET request with resilience.
        
        Args:
            endpoint: API endpoint
            **kwargs: Additional request arguments
        
        Returns:
            HTTP response
        """
        return self._make_request('GET', endpoint, **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """Make POST request with resilience.
        
        Args:
            endpoint: API endpoint
            **kwargs: Additional request arguments
        
        Returns:
            HTTP response
        """
        return self._make_request('POST', endpoint, **kwargs)
    
    def put(self, endpoint: str, **kwargs) -> requests.Response:
        """Make PUT request with resilience.
        
        Args:
            endpoint: API endpoint
            **kwargs: Additional request arguments
        
        Returns:
            HTTP response
        """
        return self._make_request('PUT', endpoint, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """Make DELETE request with resilience.
        
        Args:
            endpoint: API endpoint
            **kwargs: Additional request arguments
        
        Returns:
            HTTP response
        """
        return self._make_request('DELETE', endpoint, **kwargs)


class TrelloApiClient(ResilientApiClient):
    """Trello API client with built-in resilience.
    
    Provides convenient methods for common Trello operations used in
    board monitoring workflows. Automatically handles authentication,
    rate limiting, and error recovery.
    
    Attributes:
        api_key: Trello API key
        token: Trello authentication token
    """
    
    TRELLO_API_BASE = "https://api.trello.com/1"
    
    def __init__(self, api_key: str, token: str, requests_per_second: float = 10.0):
        """Initialize Trello API client.
        
        Args:
            api_key: Trello API key
            token: Trello authentication token
            requests_per_second: Rate limit (Trello allows 300 req/10s = 30 req/s)
        """
        super().__init__(
            base_url=self.TRELLO_API_BASE,
            requests_per_second=requests_per_second,
            max_retries=3,
            circuit_breaker_threshold=5
        )
        self.api_key = api_key
        self.token = token
        logger.info("TrelloApiClient initialized")
    
    def _auth_params(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add authentication parameters.
        
        Args:
            params: Existing parameters
        
        Returns:
            Parameters with authentication added
        """
        auth = {'key': self.api_key, 'token': self.token}
        if params:
            return {**params, **auth}
        return auth
    
    def get_card(self, card_id: str, fields: Optional[str] = None) -> Dict[str, Any]:
        """Get card details.
        
        Args:
            card_id: Trello card ID
            fields: Comma-separated list of fields to return
        
        Returns:
            Card data dictionary
        """
        params = self._auth_params()
        if fields:
            params['fields'] = fields
        
        response = self.get(f"cards/{card_id}", params=params)
        return response.json()
    
    def update_card(self, card_id: str, **kwargs) -> Dict[str, Any]:
        """Update card properties.
        
        Args:
            card_id: Trello card ID
            **kwargs: Card properties to update (name, desc, idList, etc.)
        
        Returns:
            Updated card data
        """
        params = self._auth_params(kwargs)
        response = self.put(f"cards/{card_id}", params=params)
        return response.json()
    
    def add_comment(self, card_id: str, text: str) -> Dict[str, Any]:
        """Add comment to card.
        
        Args:
            card_id: Trello card ID
            text: Comment text
        
        Returns:
            Created comment data
        """
        params = self._auth_params({'text': text})
        response = self.post(f"cards/{card_id}/actions/comments", params=params)
        return response.json()
    
    def get_cards_on_list(self, list_id: str) -> list:
        """Get all cards on a list.
        
        Args:
            list_id: Trello list ID
        
        Returns:
            List of card dictionaries
        """
        params = self._auth_params()
        response = self.get(f"lists/{list_id}/cards", params=params)
        return response.json()
    
    def move_card_to_list(self, card_id: str, list_id: str) -> Dict[str, Any]:
        """Move card to a different list.
        
        Args:
            card_id: Trello card ID
            list_id: Destination list ID
        
        Returns:
            Updated card data
        """
        return self.update_card(card_id, idList=list_id)


class PipedreamApiClient(ResilientApiClient):
    """Pipedream API client for workflow interactions.
    
    Provides methods for triggering workflows and interacting with
    Pipedream/Nebula platform APIs.
    
    Attributes:
        api_key: Pipedream API key
    """
    
    PIPEDREAM_API_BASE = "https://api.pipedream.com/v1"
    
    def __init__(self, api_key: str, requests_per_second: float = 5.0):
        """Initialize Pipedream API client.
        
        Args:
            api_key: Pipedream API key
            requests_per_second: Rate limit
        """
        super().__init__(
            base_url=self.PIPEDREAM_API_BASE,
            requests_per_second=requests_per_second,
            max_retries=3,
            circuit_breaker_threshold=5
        )
        self.api_key = api_key
        self.session.headers.update({'Authorization': f'Bearer {api_key}'})
        logger.info("PipedreamApiClient initialized")
    
    def trigger_workflow(self, workflow_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger a Pipedream workflow.
        
        Args:
            workflow_id: Pipedream workflow ID
            data: Data to send to workflow
        
        Returns:
            Trigger response data
        """
        response = self.post(f"sources/{workflow_id}/event", json=data)
        return response.json() if response.text else {'status': 'triggered'}
    
    def get_workflow_events(self, workflow_id: str, limit: int = 10) -> list:
        """Get recent workflow events.
        
        Args:
            workflow_id: Pipedream workflow ID
            limit: Maximum number of events to return
        
        Returns:
            List of event dictionaries
        """
        params = {'limit': limit}
        response = self.get(f"sources/{workflow_id}/events", params=params)
        return response.json()
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get authenticated account information.
        
        Returns:
            Account data dictionary
        """
        response = self.get('users/me')
        return response.json()


if __name__ == "__main__":
    """Example usage demonstrating API resilience patterns."""
    
    print("=== API Resilience Demo ===")
    
    # Example 1: Rate limiting demonstration
    print("\n1. Rate Limiter Demo:")
    limiter = RateLimitHandler(requests_per_second=2.0, bucket_size=5)
    
    print("   Acquiring tokens rapidly (should throttle):")
    for i in range(10):
        start = time.time()
        success = limiter.acquire(tokens=1, timeout=5.0)
        elapsed = time.time() - start
        print(f"   Request {i+1}: {success} (waited {elapsed:.2f}s)")
    
    # Example 2: Trello API client usage (mock credentials)
    print("\n2. Trello API Client Demo:")
    print("   Note: Using mock credentials - will fail auth but demonstrates resilience")
    
    try:
        trello = TrelloApiClient(
            api_key='mock_api_key',
            token='mock_token',
            requests_per_second=10.0
        )
        
        # This will fail auth but shows circuit breaker and retry logic
        print("   Attempting to get card (will fail auth):")
        card = trello.get_card('mock_card_id')
        print(f"   Card: {card}")
    except Exception as e:
        print(f"   Expected error: {type(e).__name__}: {str(e)[:100]}")
    
    # Example 3: Circuit breaker demonstration
    print("\n3. Circuit Breaker Demo:")
    breaker = CircuitBreaker(failure_threshold=3, timeout=5)
    
    def failing_operation():
        raise Exception("Simulated failure")
    
    print("   Testing circuit breaker with failing operation:")
    for i in range(5):
        try:
            breaker.call(failing_operation)
        except CircuitBreakerOpen:
            print(f"   Attempt {i+1}: Circuit breaker is OPEN (preventing further calls)")
        except Exception as e:
            print(f"   Attempt {i+1}: Failed - {e}")
    
    # Example 4: Error tracking stats
    print("\n4. Error Tracking Statistics:")
    stats = error_tracker.get_error_stats()
    print(f"   Total errors logged: {stats['total_errors']}")
    print(f"   Error types: {stats['error_counts']}")
    if stats['recent_errors']:
        print(f"   Most recent error: {stats['recent_errors'][-1]['error_type']}")
    
    print("\n=== Demo Complete ===")
