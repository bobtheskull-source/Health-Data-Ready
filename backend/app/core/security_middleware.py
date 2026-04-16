from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import hashlib
import time
import re

class RateLimiter:
    """Simple in-memory rate limiter. Use Redis in production."""
    
    def __init__(self):
        self._store: Dict[str, List[float]] = {}
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
    
    def _cleanup(self):
        """Remove expired entries."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        cutoff = now - 3600  # 1 hour ago
        for key in list(self._store.keys()):
            self._store[key] = [t for t in self._store[key] if t > cutoff]
            if not self._store[key]:
                del self._store[key]
        self._last_cleanup = now
    
    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Check if request is allowed under rate limit."""
        self._cleanup()
        now = time.time()
        window_start = now - window_seconds
        
        if key not in self._store:
            self._store[key] = []
        
        # Filter to current window
        self._store[key] = [t for t in self._store[key] if t > window_start]
        
        if len(self._store[key]) >= max_requests:
            return False
        
        self._store[key].append(now)
        return True

# Global rate limiter instance
_rate_limiter = RateLimiter()

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://bobtheskull-source.github.io; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' https://bobtheskull-source.github.io; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # XSS Protection
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )
        
        # Strict Transport Security (HTTPS only)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for sensitive endpoints."""
    
    def __init__(self, app, auth_limit: int = 5, auth_window: int = 300):
        super().__init__(app)
        self.auth_limit = auth_limit  # 5 attempts
        self.auth_window = auth_window  # 5 minutes
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Only rate limit auth endpoints
        if request.url.path in ["/api/v1/auth/login", "/api/v1/auth/register"]:
            # Get client IP (handle proxies)
            client_ip = self._get_client_ip(request)
            key = f"auth:{client_ip}:{request.url.path}"
            
            if not _rate_limiter.is_allowed(key, self.auth_limit, self.auth_window):
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Too many attempts. Please try again later.",
                        "retry_after": self.auth_window
                    },
                    headers={"Retry-After": str(self.auth_window)}
                )
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Get real client IP behind proxy."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        return request.client.host if request.client else "unknown"

class InputValidationMiddleware(BaseHTTPMiddleware):
    """Validate and sanitize input data."""
    
    # SQL injection patterns
    SQLI_PATTERNS = [
        r"(\%27)|(\')|(\-\-)|(\%23)|(#)",
        r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))",
        r"\w*((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))",
        r"((\%27)|(\'))union",
        r"exec(\s|\+)+(s|x)p\w+",
        r"UNION\s+SELECT",
        r"INSERT\s+INTO",
        r"DELETE\s+FROM",
        r"DROP\s+TABLE"
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>[\s\S]*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<object",
        r"<embed"
    ]
    
    MAX_BODY_SIZE = 1024 * 1024  # 1MB max body
    MAX_PARAM_LENGTH = 10000  # Max param length
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_BODY_SIZE:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Request body too large"}
            )
        
        # Validate query parameters
        for key, values in request.query_params.multi_items():
            if len(key) > self.MAX_PARAM_LENGTH or any(len(v) > self.MAX_PARAM_LENGTH for v in values):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Parameter too long"}
                )
            
            # Check for injection patterns
            if self._contains_injection(key) or any(self._contains_injection(v) for v in values):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid input detected"}
                )
        
        return await call_next(request)
    
    def _contains_injection(self, value: str) -> bool:
        """Check if value contains SQLi or XSS patterns."""
        if not value:
            return False
        
        value_lower = value.lower()
        
        for pattern in self.SQLI_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        
        return False

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add request ID for tracing."""
    
    async def dispatch(self, request: Request, call_next: Callable):
        import uuid
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response
