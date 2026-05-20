"""Metricas simples via Redis.

Evitamos dependencia de Prometheus por ora; o que precisamos e basico:
contadores de tool, cache hit/miss, modelo usado e latencia agregada
(count + sum_ms para p_medio). A ideia e ter visibilidade do chat em
producao sem pagar o custo de instrumentacao pesada.

Todos os helpers degradam silenciosamente quando o Redis nao esta
disponivel — jamais devem matar uma request por falha de telemetria.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from app.cache import get_redis

logger = logging.getLogger(__name__)

_PREFIX = "metrics:"

async def incr(metric: str, by: int = 1) -> None:
    try:
        r = await get_redis()
        await r.incr(f"{_PREFIX}{metric}", by)
    except Exception as e:
        logger.debug("metric incr failed: %s", e)

async def incr_by_dim(metric: str, dim: str, by: int = 1) -> None:
    """Incrementa um contador particionado por dimensao (ex: modelo usado)."""
    try:
        r = await get_redis()
        await r.hincrby(f"{_PREFIX}{metric}", dim, by)
    except Exception as e:
        logger.debug("metric incr_by_dim failed: %s", e)

async def observe_ms(metric: str, ms: int) -> None:
    """Agrega latencias: count e sum_ms. Media = sum_ms/count."""
    try:
        r = await get_redis()
        pipe = r.pipeline()
        pipe.hincrby(f"{_PREFIX}{metric}", "count", 1)
        pipe.hincrbyfloat(f"{_PREFIX}{metric}", "sum_ms", float(ms))
        await pipe.execute()
    except Exception as e:
        logger.debug("metric observe_ms failed: %s", e)

@asynccontextmanager
async def time_ms(metric: str):
    """Context manager que observa duracao do bloco em ms."""
    t0 = time.perf_counter()
    try:
        yield
    finally:
        ms = int((time.perf_counter() - t0) * 1000)
        await observe_ms(metric, ms)

async def snapshot() -> dict:
    """Retorna snapshot de todas as metricas (string counters + hashes)."""
    try:
        r = await get_redis()
        keys = await r.keys(f"{_PREFIX}*")
        result: dict = {}
        for k in keys:
            kname = k.removeprefix(_PREFIX) if isinstance(k, str) else k
            key_type = await r.type(k)
            if key_type == "string":
                val = await r.get(k)
                result[kname] = int(val) if val is not None else 0
            elif key_type == "hash":
                data = await r.hgetall(k)

                parsed = {}
                for field, val in data.items():
                    try:
                        parsed[field] = float(val) if "." in str(val) else int(val)
                    except (TypeError, ValueError):
                        parsed[field] = val

                if "count" in parsed and "sum_ms" in parsed and parsed["count"]:
                    parsed["avg_ms"] = round(parsed["sum_ms"] / parsed["count"], 2)
                result[kname] = parsed
        return result
    except Exception as e:
        logger.warning("metric snapshot failed: %s", e)
        return {}
