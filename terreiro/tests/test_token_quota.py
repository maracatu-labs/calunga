"""Tests for the daily Gemini token quota per user."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.services import token_quota


class TestCharsToTokens:
    def test_approximates_chars_divided_by_four(self):
        assert token_quota._chars_to_tokens(4) == 1
        assert token_quota._chars_to_tokens(100) == 25

    def test_rounds_down(self):
        assert token_quota._chars_to_tokens(7) == 1

    def test_minimum_is_one(self):
        assert token_quota._chars_to_tokens(0) == 1
        assert token_quota._chars_to_tokens(3) == 1

class TestCheckQuota:
    @pytest.mark.asyncio
    async def test_passes_when_below_limit(self, monkeypatch):
        fake_redis = AsyncMock()
        fake_redis.get = AsyncMock(return_value="100")
        monkeypatch.setattr(token_quota, "get_redis", AsyncMock(return_value=fake_redis))

        await token_quota.check_quota("user-1")

    @pytest.mark.asyncio
    async def test_raises_429_when_input_overflows(self, monkeypatch):
        fake_redis = AsyncMock()
        fake_redis.get = AsyncMock(side_effect=lambda key: "999999" if ":in:" in key else "0")
        monkeypatch.setattr(token_quota, "get_redis", AsyncMock(return_value=fake_redis))

        with pytest.raises(HTTPException) as exc:
            await token_quota.check_quota("user-1")
        assert exc.value.status_code == 429
        assert "Cota" in exc.value.detail["erro"]

    @pytest.mark.asyncio
    async def test_raises_429_when_output_overflows(self, monkeypatch):
        fake_redis = AsyncMock()
        fake_redis.get = AsyncMock(side_effect=lambda key: "999999" if ":out:" in key else "0")
        monkeypatch.setattr(token_quota, "get_redis", AsyncMock(return_value=fake_redis))

        with pytest.raises(HTTPException) as exc:
            await token_quota.check_quota("user-1")
        assert exc.value.status_code == 429

    @pytest.mark.asyncio
    async def test_fails_open_when_redis_is_down(self, monkeypatch):
        async def broken():
            raise RuntimeError("redis down")
        monkeypatch.setattr(token_quota, "get_redis", broken)

        await token_quota.check_quota("user-1")

    @pytest.mark.asyncio
    async def test_passes_with_no_prior_usage(self, monkeypatch):
        fake_redis = AsyncMock()
        fake_redis.get = AsyncMock(return_value=None)
        monkeypatch.setattr(token_quota, "get_redis", AsyncMock(return_value=fake_redis))

        await token_quota.check_quota("user-1")

class TestRecordUsage:
    @pytest.mark.asyncio
    async def test_increments_input_and_output(self, monkeypatch):
        fake_redis = MagicMock()
        pipe = MagicMock()
        pipe.execute = AsyncMock(return_value=[1, 1, 1, 1])
        fake_redis.pipeline = MagicMock(return_value=pipe)
        monkeypatch.setattr(token_quota, "get_redis", AsyncMock(return_value=fake_redis))

        await token_quota.record_usage("user-1", input_chars=400, output_chars=200)

        assert pipe.incrby.call_count == 2
        assert pipe.expire.call_count == 2
        pipe.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fails_silently_when_redis_is_down(self, monkeypatch):
        async def broken():
            raise RuntimeError("redis down")
        monkeypatch.setattr(token_quota, "get_redis", broken)

        await token_quota.record_usage("user-1", 100, 50)
