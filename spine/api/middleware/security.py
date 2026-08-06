"""Security headers and lightweight rate limiting."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from spine.config.settings import settings

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-site",
}

if settings.is_production:
    _SECURITY_HEADERS["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

_LOGIN_WINDOW_SECONDS = 60
_login_attempts: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _rate_limit_login(ip: str) -> bool:
    now = time.monotonic()
    window = _login_attempts[ip]
    while window and now - window[0] > _LOGIN_WINDOW_SECONDS:
        window.popleft()
    if len(window) >= settings.login_rate_limit_per_minute:
        return False
    window.append(now)
    return True


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if (
            settings.login_rate_limit_per_minute > 0
            and request.method == "POST"
            and request.url.path.rstrip("/") == "/v1/auth/login"
        ):
            ip = _client_ip(request)
            if not _rate_limit_login(ip):
                return Response(
                    content='{"detail":"Too many login attempts. Try again later."}',
                    status_code=429,
                    media_type="application/json",
                    headers=_SECURITY_HEADERS,
                )

        response = await call_next(request)
        for key, value in _SECURITY_HEADERS.items():
            if key not in response.headers:
                response.headers[key] = value
        return response
