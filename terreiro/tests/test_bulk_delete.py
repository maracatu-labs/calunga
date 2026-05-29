"""Tests for the bulk-delete query and route helper."""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.queries import conversas as conversas_q


class TestDeletarTodasConversas:
    @pytest.mark.asyncio
    async def test_returns_zero_when_no_conversations(self):
        pool = AsyncMock()
        pool.execute = AsyncMock(return_value="DELETE 0")
        user_id = uuid.uuid4()

        count = await conversas_q.deletar_todas_conversas(pool, user_id)

        assert count == 0
        pool.execute.assert_awaited_once_with(
            "DELETE FROM conversas WHERE user_id = $1", user_id
        )

    @pytest.mark.asyncio
    async def test_returns_count_when_deletions_happen(self):
        pool = AsyncMock()
        pool.execute = AsyncMock(return_value="DELETE 7")

        count = await conversas_q.deletar_todas_conversas(pool, uuid.uuid4())

        assert count == 7

    @pytest.mark.asyncio
    async def test_returns_zero_on_unexpected_tag(self):
        pool = AsyncMock()
        pool.execute = AsyncMock(return_value="UPDATE 3")

        count = await conversas_q.deletar_todas_conversas(pool, uuid.uuid4())

        assert count == 0

    @pytest.mark.asyncio
    async def test_filters_by_user_id(self):
        pool = AsyncMock()
        pool.execute = AsyncMock(return_value="DELETE 2")
        user_id = uuid.uuid4()

        await conversas_q.deletar_todas_conversas(pool, user_id)

        args, _ = pool.execute.call_args
        assert args[1] == user_id
