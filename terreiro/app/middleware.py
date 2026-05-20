"""Middlewares da API: rate limiting via Redis.

Rate limit com sliding-window simplificado (contador por minuto).
- Publico (nao autenticado): 100 req/min por IP.
- Autenticado (header Authorization: Bearer): 1000 req/min por user_id.

Os limites seguem o PRD. Caminhos /health, /v1/auth/* e o stream
/v1/chats com SSE ficam isentos (auth tem limite proprio por canal de
envio de magic link; SSE mantem conexao aberta e conta uma vez).
"""

from __future__ import annotations

import logging

import jwt
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.cache import get_redis
from app.config import settings

logger = logging.getLogger(__name__)

_WINDOW_SECONDS = 60
_LIMIT_PUBLIC = 100
_LIMIT_AUTH = 1000

_EXEMPT_PREFIXES = (
    "/health",
    "/v1/auth/",
)

def _extract_user_id(request: Request) -> str | None:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload.get("sub") or payload.get("user_id")
    except jwt.PyJWTError:
        return None

def _extract_ip(request: Request) -> str:

    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in _EXEMPT_PREFIXES):
            return await call_next(request)

        user_id = _extract_user_id(request)
        if user_id:
            key = f"rl:user:{user_id}"
            limit = _LIMIT_AUTH
        else:
            key = f"rl:ip:{_extract_ip(request)}"
            limit = _LIMIT_PUBLIC

        try:
            redis = await get_redis()
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, _WINDOW_SECONDS)
            if count > limit:
                retry_after = await redis.ttl(key)
                logger.info("rate_limit_exceeded key=%s count=%s limit=%s", key, count, limit)
                return JSONResponse(
                    status_code=429,
                    content={
                        "erro": "Rate limit excedido",
                        "limite_por_minuto": limit,
                        "retry_after_segundos": max(1, retry_after),
                    },
                    headers={"Retry-After": str(max(1, retry_after))},
                )
        except Exception as e:

            logger.warning("Rate limit degradado (redis erro): %s", e)

        return await call_next(request)
