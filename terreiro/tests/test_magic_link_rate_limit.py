"""Tests for the /v1/auth/magic-link rate limit."""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.routers import auth as auth_router


class TestEnforceMagicLinkLimit:
    @pytest.mark.asyncio
    async def test_passes_within_limit(self, monkeypatch):
        fake_redis = AsyncMock()
        fake_redis.incr = AsyncMock(return_value=1)
        fake_redis.expire = AsyncMock(return_value=True)
        monkeypatch.setattr(auth_router, "get_redis", AsyncMock(return_value=fake_redis))

        await auth_router._enforce_magic_link_limit("rl:magic:email:a@b.com", limit=3, label="email")

        fake_redis.expire.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_does_not_re_expire_on_subsequent_call(self, monkeypatch):
        fake_redis = AsyncMock()
        fake_redis.incr = AsyncMock(return_value=2)
        fake_redis.expire = AsyncMock()
        monkeypatch.setattr(auth_router, "get_redis", AsyncMock(return_value=fake_redis))

        await auth_router._enforce_magic_link_limit("k", limit=3, label="email")

        fake_redis.expire.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_429_when_limit_exceeded(self, monkeypatch):
        fake_redis = AsyncMock()
        fake_redis.incr = AsyncMock(return_value=4)
        fake_redis.ttl = AsyncMock(return_value=2400)
        monkeypatch.setattr(auth_router, "get_redis", AsyncMock(return_value=fake_redis))

        with pytest.raises(HTTPException) as exc:
            await auth_router._enforce_magic_link_limit("k", limit=3, label="email")
        assert exc.value.status_code == 429
        assert exc.value.detail["retry_after_segundos"] == 2400
        assert exc.value.headers["Retry-After"] == "2400"

    @pytest.mark.asyncio
    async def test_retry_after_floored_at_one(self, monkeypatch):
        fake_redis = AsyncMock()
        fake_redis.incr = AsyncMock(return_value=4)
        fake_redis.ttl = AsyncMock(return_value=-1)
        monkeypatch.setattr(auth_router, "get_redis", AsyncMock(return_value=fake_redis))

        with pytest.raises(HTTPException) as exc:
            await auth_router._enforce_magic_link_limit("k", limit=3, label="email")
        assert exc.value.detail["retry_after_segundos"] == 1

    @pytest.mark.asyncio
    async def test_fails_open_when_redis_is_down(self, monkeypatch):
        async def broken():
            raise RuntimeError("redis down")
        monkeypatch.setattr(auth_router, "get_redis", broken)

        await auth_router._enforce_magic_link_limit("k", limit=3, label="email")
