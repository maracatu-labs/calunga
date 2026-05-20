"""Testes do modulo de metricas (contadores + latencias via Redis)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app import metrics

@pytest.mark.asyncio
async def test_incr_incrementa_contador(monkeypatch):
    fake = AsyncMock()
    fake.incr = AsyncMock()
    monkeypatch.setattr(metrics, "get_redis", AsyncMock(return_value=fake))

    await metrics.incr("chat.error", by=2)
    fake.incr.assert_awaited_once_with("metrics:chat.error", 2)

@pytest.mark.asyncio
async def test_incr_by_dim_usa_hash(monkeypatch):
    fake = AsyncMock()
    fake.hincrby = AsyncMock()
    monkeypatch.setattr(metrics, "get_redis", AsyncMock(return_value=fake))

    await metrics.incr_by_dim("model.used", "gemini-2.5-pro")
    fake.hincrby.assert_awaited_once_with("metrics:model.used", "gemini-2.5-pro", 1)

@pytest.mark.asyncio
async def test_observe_ms_agrega_count_e_sum(monkeypatch):
    fake = AsyncMock()
    pipe = MagicMock()
    pipe.execute = AsyncMock()
    fake.pipeline = MagicMock(return_value=pipe)
    monkeypatch.setattr(metrics, "get_redis", AsyncMock(return_value=fake))

    await metrics.observe_ms("chat.ainvoke", 420)

    pipe.hincrby.assert_called_with("metrics:chat.ainvoke", "count", 1)
    pipe.hincrbyfloat.assert_called_with("metrics:chat.ainvoke", "sum_ms", 420.0)
    pipe.execute.assert_awaited_once()

@pytest.mark.asyncio
async def test_time_ms_observa_mesmo_em_excecao(monkeypatch):
    observed: list = []

    async def fake_observe(metric: str, ms: int):
        observed.append((metric, ms))

    monkeypatch.setattr(metrics, "observe_ms", fake_observe)

    with pytest.raises(RuntimeError):
        async with metrics.time_ms("chat.broken"):
            raise RuntimeError("boom")

    assert len(observed) == 1
    assert observed[0][0] == "chat.broken"

@pytest.mark.asyncio
async def test_helpers_degradam_sem_redis(monkeypatch):
    async def broken():
        raise RuntimeError("no redis")
    monkeypatch.setattr(metrics, "get_redis", broken)

    await metrics.incr("x")
    await metrics.incr_by_dim("x", "dim")
    await metrics.observe_ms("x", 10)

@pytest.mark.asyncio
async def test_snapshot_calcula_avg_ms(monkeypatch):
    fake = AsyncMock()
    fake.keys = AsyncMock(return_value=["metrics:chat.ainvoke.flash", "metrics:cache.hit"])

    async def fake_type(key):
        return "hash" if key == "metrics:chat.ainvoke.flash" else "string"

    fake.type = fake_type
    fake.get = AsyncMock(return_value="42")
    fake.hgetall = AsyncMock(return_value={"count": "4", "sum_ms": "2000.0"})

    monkeypatch.setattr(metrics, "get_redis", AsyncMock(return_value=fake))

    data = await metrics.snapshot()
    assert data["cache.hit"] == 42
    entry = data["chat.ainvoke.flash"]
    assert entry["count"] == 4
    assert entry["sum_ms"] == 2000.0
    assert entry["avg_ms"] == 500.0
