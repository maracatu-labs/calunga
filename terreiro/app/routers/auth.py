import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth import criar_jwt, get_current_user
from app.cache import get_redis
from app.config import settings
from app.database import get_pool
from app.middleware import extract_ip
from app.queries import auth as auth_q
from app.schemas.auth import (
    AuthResponse,
    MagicLinkRequest,
    MagicLinkResponse,
    UserResponse,
    VerifyRequest,
)
from app.services.email import enviar_magic_link

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/auth", tags=["auth"])

_MAGIC_LINK_WINDOW_SECONDS = 3600

async def _enforce_magic_link_limit(key: str, limit: int, label: str) -> None:
    """Fixed 1h window rate limit on a Redis key. Raises 429 when exceeded.

    Fails open when Redis is down: better to let magic-link through than to
    block a legitimate user from logging in. The Resend monthly budget is the
    last-resort financial protection.
    """
    try:
        redis = await get_redis()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, _MAGIC_LINK_WINDOW_SECONDS)
        if count > limit:
            retry_after = max(1, await redis.ttl(key))
        else:
            return
    except Exception as e:
        logger.warning("magic_link_rate_limit_degraded redis_error=%s", e)
        return

    logger.info("magic_link_rate_limit_exceeded label=%s count=%s limit=%s", label, count, limit)
    raise HTTPException(
        status_code=429,
        detail={
            "erro": "Muitas solicitações de link de acesso. Tente novamente em alguns minutos.",
            "retry_after_segundos": retry_after,
        },
        headers={"Retry-After": str(retry_after)},
    )

@router.post("/magic-link", response_model=MagicLinkResponse)
async def request_magic_link(payload: MagicLinkRequest, request: Request):
    email = payload.email.lower().strip()
    ip = extract_ip(request)
    await _enforce_magic_link_limit(
        key=f"rl:magic:email:{email}",
        limit=settings.magic_link_email_limit_hour,
        label="email",
    )
    await _enforce_magic_link_limit(
        key=f"rl:magic:ip:{ip}",
        limit=settings.magic_link_ip_limit_hour,
        label="ip",
    )

    pool = get_pool()
    token_id = await auth_q.criar_magic_link(pool, email)
    await enviar_magic_link(email, str(token_id))
    return MagicLinkResponse(message="Link enviado para seu email")

@router.post("/verify", response_model=AuthResponse)
async def verify_magic_link(request: VerifyRequest):
    pool = get_pool()
    email = await auth_q.validar_magic_link(pool, request.token)

    if not email:
        raise HTTPException(status_code=400, detail="Link inválido ou expirado")

    await auth_q.marcar_magic_link_usado(pool, request.token)
    user = await auth_q.buscar_ou_criar_user(pool, email)
    jwt_token = criar_jwt(uuid.UUID(str(user["id"])), user["email"])

    return AuthResponse(
        token=jwt_token,
        user=UserResponse(id=user["id"], email=user["email"]),
    )

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}
