"""Cache de respostas do Calunga (chave exata + semantico).

Chaveado por (conversa_id, mensagem, modelo). A chave por conversa existe
porque perguntas dependentes do contexto ("E ele?", "Quem e essa pessoa?")
deveriam bater em conversas diferentes; antes a resposta cacheada vazava
entre chats distintos. Quando conversa_id e omitido, o cache degrada para
um bucket global ("global") que so ajuda em perguntas genericas o bastante.
"""

import hashlib
import json
import logging

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None

CACHE_TTL = 3600
_GLOBAL_BUCKET = "global"

async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis

async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None

def _bucket(conversa_id: str | None) -> str:
    return str(conversa_id) if conversa_id else _GLOBAL_BUCKET

def _cache_key(message: str, model: str, conversa_id: str | None) -> str:
    raw = f"{_bucket(conversa_id)}:{model}:{message.strip().lower()}"
    return f"chat:{hashlib.sha256(raw.encode()).hexdigest()}"

async def get_cached_response(
    message: str,
    model: str,
    conversa_id: str | None = None,
) -> str | None:
    try:
        r = await get_redis()
        return await r.get(_cache_key(message, model, conversa_id))
    except Exception as e:
        logger.warning(f"Cache read error: {e}")
        return None

async def set_cached_response(
    message: str,
    model: str,
    response: str,
    conversa_id: str | None = None,
) -> None:
    try:
        r = await get_redis()
        await r.set(_cache_key(message, model, conversa_id), response, ex=CACHE_TTL)
    except Exception as e:
        logger.warning(f"Cache write error: {e}")

SEMANTIC_THRESHOLD = 0.92

def _semantic_key(conversa_id: str | None) -> str:
    return f"semcache:{_bucket(conversa_id)}"

async def get_semantic_cached_response(
    message: str,
    embedding: list[float] | None,
    conversa_id: str | None = None,
) -> str | None:
    """Busca resposta cacheada por similaridade semantica dentro da conversa."""
    if not embedding:
        return None

    try:
        r = await get_redis()
        entries = await r.lrange(_semantic_key(conversa_id), 0, 200)

        for entry_json in entries:
            entry = json.loads(entry_json)
            cached_emb = entry["embedding"]
            similarity = _cosine_similarity(embedding, cached_emb)
            if similarity >= SEMANTIC_THRESHOLD:
                logger.info(
                    "Semantic cache hit bucket=%s similarity=%.3f",
                    _bucket(conversa_id),
                    similarity,
                )
                return entry["response"]

    except Exception as e:
        logger.warning(f"Semantic cache read error: {e}")
    return None

async def set_semantic_cached_response(
    message: str,
    embedding: list[float] | None,
    response: str,
    conversa_id: str | None = None,
) -> None:
    """Salva resposta no cache semantico da conversa."""
    if not embedding:
        return

    try:
        r = await get_redis()
        key = _semantic_key(conversa_id)
        entry = json.dumps({"message": message, "embedding": embedding, "response": response})
        await r.lpush(key, entry)
        await r.ltrim(key, 0, 199)
        await r.expire(key, CACHE_TTL)
    except Exception as e:
        logger.warning(f"Semantic cache write error: {e}")

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
