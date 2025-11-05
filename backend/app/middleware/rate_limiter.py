"""
Rate limiting middleware for API protection.
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.services.analytics_service import check_rate_limit, log_api_usage
import time
import logging

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with configurable limits.

    Default limits:
    - 100 requests per minute for authenticated users
    - 20 requests per minute for anonymous users
    - 1000 requests per hour for API keys
    """

    def __init__(self, app, requests_per_minute: int = 100, requests_per_minute_anon: int = 20):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_minute_anon = requests_per_minute_anon

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Skip rate limiting for health check and docs
        if request.url.path in ['/health', '/docs', '/redoc', '/openapi.json']:
            return await call_next(request)

        # Extract user identification
        user_id = None
        api_key = None

        # Check for API key in headers
        api_key_header = request.headers.get('X-API-Key')
        if api_key_header:
            api_key = api_key_header
            # TODO: Validate API key and get user_id

        # Check for JWT token
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            # TODO: Decode JWT and get user_id
            pass

        # Determine rate limit
        limit = self.requests_per_minute if (user_id or api_key) else self.requests_per_minute_anon

        # Check rate limit
        if not check_rate_limit(user_id, api_key, limit=limit, window_minutes=1):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {limit} requests per minute allowed",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"Request processing error: {str(e)}")
            response = JSONResponse(
                status_code=500,
                content={"error": "Internal server error"}
            )

        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)

        # Log API usage (async, non-blocking)
        try:
            log_api_usage(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                user_id=user_id,
                api_key=api_key,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get('user-agent')
            )
        except Exception as log_error:
            # Don't fail the request if logging fails
            logger.warning(f"Failed to log API usage: {str(log_error)}")

        # Add rate limit headers
        response.headers['X-RateLimit-Limit'] = str(limit)
        response.headers['X-Response-Time'] = f"{response_time_ms}ms"

        return response


class IPBasedRateLimiter(BaseHTTPMiddleware):
    """Simple IP-based rate limiter using in-memory storage."""

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_counts = {}  # {ip: [(timestamp, count), ...]}

    async def dispatch(self, request: Request, call_next):
        # Skip for health checks
        if request.url.path in ['/health', '/docs', '/redoc', '/openapi.json']:
            return await call_next(request)

        client_ip = request.client.host if request.client else 'unknown'
        current_time = time.time()

        # Clean old entries
        if client_ip in self.request_counts:
            self.request_counts[client_ip] = [
                (ts, count) for ts, count in self.request_counts[client_ip]
                if current_time - ts < self.window_seconds
            ]

        # Count requests in current window
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []

        request_count = sum(count for _, count in self.request_counts[client_ip])

        if request_count >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.max_requests} requests per {self.window_seconds} seconds",
                    "retry_after": self.window_seconds
                },
                headers={"Retry-After": str(self.window_seconds)}
            )

        # Add current request
        self.request_counts[client_ip].append((current_time, 1))

        # Process request
        response = await call_next(request)

        # Add rate limit info to headers
        response.headers['X-RateLimit-Limit'] = str(self.max_requests)
        response.headers['X-RateLimit-Remaining'] = str(max(0, self.max_requests - request_count - 1))
        response.headers['X-RateLimit-Reset'] = str(int(current_time + self.window_seconds))

        return response
