"""Daily Gemini token quota per user.

Tracks input + output tokens consumed per user_id within a 24h window, with a
25h TTL in Redis. Tokens are approximated via chars/4 — good enough for budget
protection and avoids a remote tokenizer dependency.

Fails open: if Redis is unreachable, the call does not block the chat (it logs
a warning). The last-resort financial protection is the hard budget cap on
Google Cloud.
"""

from __future__ import annotations

import logging
from datetime import date

from fastapi import HTTPException

from app.cache import get_redis
from app.config import settings

logger = logging.getLogger(__name__)

_TTL_SECONDS = 25 * 3600
_CHARS_PER_TOKEN = 4

def _chars_to_tokens(chars: int) -> int:
    return max(1, chars // _CHARS_PER_TOKEN)

def _key(user_id: str, kind: str) -> str:
    return f"tokens:{kind}:{user_id}:{date.today().isoformat()}"

async def check_quota(user_id: str) -> None:
    """Raise 429 when the user has exceeded the daily quota."""
    try:
        redis = await get_redis()
        in_used = int(await redis.get(_key(user_id, "in")) or 0)
        out_used = int(await redis.get(_key(user_id, "out")) or 0)
    except Exception as e:
        logger.warning("token_quota_check_degraded redis_error=%s", e)
        return

    in_limit = settings.token_quota_daily_input
    out_limit = settings.token_quota_daily_output
    if in_used >= in_limit or out_used >= out_limit:
        logger.info(
            "token_quota_exceeded user=%s in=%s/%s out=%s/%s",
            user_id, in_used, in_limit, out_used, out_limit,
        )
        raise HTTPException(
            status_code=429,
            detail={
                "erro": "Cota diária da IA esgotada. Tente novamente amanhã.",
                "input_tokens_usados": in_used,
                "input_tokens_limite": in_limit,
                "output_tokens_usados": out_used,
                "output_tokens_limite": out_limit,
            },
            headers={"Retry-After": "3600"},
        )

async def record_usage(user_id: str, input_chars: int, output_chars: int) -> None:
    """Increment daily counters (tokens estimated via chars/4)."""
    in_tokens = _chars_to_tokens(input_chars)
    out_tokens = _chars_to_tokens(output_chars)
    try:
        redis = await get_redis()
        in_key = _key(user_id, "in")
        out_key = _key(user_id, "out")
        pipe = redis.pipeline()
        pipe.incrby(in_key, in_tokens)
        pipe.expire(in_key, _TTL_SECONDS)
        pipe.incrby(out_key, out_tokens)
        pipe.expire(out_key, _TTL_SECONDS)
        await pipe.execute()
    except Exception as e:
        logger.warning("token_quota_record_failed redis_error=%s", e)
