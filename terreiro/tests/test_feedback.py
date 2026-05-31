"""Tests for message feedback persistence (like/dislike) and tool_calls decoding."""

import uuid

import pytest

from app.queries import conversas as conversas_q
from app.queries import feedback as feedback_q
from tests.conftest import record


class TestRegistrarFeedback:
    @pytest.mark.asyncio
    async def test_returns_true_when_row_inserted(self, fake_pool):
        fake_pool.fetchrow.return_value = record(id=uuid.uuid4())
        ok = await feedback_q.registrar_feedback(fake_pool, uuid.uuid4(), uuid.uuid4(), "like")
        assert ok is True

    @pytest.mark.asyncio
    async def test_returns_false_when_not_owned_or_missing(self, fake_pool):
        fake_pool.fetchrow.return_value = None
        ok = await feedback_q.registrar_feedback(
            fake_pool, uuid.uuid4(), uuid.uuid4(), "dislike", "Informação incorreta", "errou o partido"
        )
        assert ok is False

    @pytest.mark.asyncio
    async def test_passes_optional_details_as_params(self, fake_pool):
        fake_pool.fetchrow.return_value = record(id=uuid.uuid4())
        mensagem_id = uuid.uuid4()
        await feedback_q.registrar_feedback(
            fake_pool, mensagem_id, uuid.uuid4(), "dislike", "Link ou fonte incorreta", "link errado"
        )
        args = fake_pool.fetchrow.call_args.args
        # ($1 query, mensagem_id, user_id, tipo, categoria, comentario)
        assert args[1] == mensagem_id
        assert args[3] == "dislike"
        assert args[4] == "Link ou fonte incorreta"
        assert args[5] == "link errado"


class TestUltimosFeedbacks:
    @pytest.mark.asyncio
    async def test_maps_message_id_to_latest_tipo(self, fake_pool):
        m1, m2 = uuid.uuid4(), uuid.uuid4()
        fake_pool.fetch.return_value = [
            record(mensagem_id=m1, tipo="like"),
            record(mensagem_id=m2, tipo="dislike"),
        ]
        out = await feedback_q.ultimos_feedbacks(fake_pool, uuid.uuid4(), uuid.uuid4())
        assert out == {m1: "like", m2: "dislike"}

    @pytest.mark.asyncio
    async def test_empty_when_no_feedback(self, fake_pool):
        fake_pool.fetch.return_value = []
        out = await feedback_q.ultimos_feedbacks(fake_pool, uuid.uuid4(), uuid.uuid4())
        assert out == {}


class TestDecodeMessages:
    def test_parses_tool_calls_json_string(self):
        rows = [
            record(
                id=1,
                role="assistant",
                content="oi",
                tool_calls='[{"type": "tool_start", "tool": "buscar_despesas"}]',
                created_at=None,
            )
        ]
        out = conversas_q._decode_messages(rows)
        assert out[0]["tool_calls"] == [{"type": "tool_start", "tool": "buscar_despesas"}]

    def test_handles_null_tool_calls(self):
        rows = [record(id=1, role="user", content="oi", tool_calls=None, created_at=None)]
        out = conversas_q._decode_messages(rows)
        assert out[0]["tool_calls"] is None

    def test_handles_invalid_json(self):
        rows = [record(id=1, role="assistant", content="oi", tool_calls="{not json", created_at=None)]
        out = conversas_q._decode_messages(rows)
        assert out[0]["tool_calls"] is None
