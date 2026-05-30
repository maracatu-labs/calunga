"""Tests for message feedback persistence (like/dislike) and tool_calls decoding."""

import uuid
from datetime import datetime

import pytest

from app.queries import conversas as conversas_q
from app.queries import feedback as feedback_q
from tests.conftest import record


class TestRegistrarFeedback:
    @pytest.mark.asyncio
    async def test_returns_true_when_row_inserted(self, fake_pool):
        fake_pool.fetchrow.return_value = record(id=1)
        ok = await feedback_q.registrar_feedback(fake_pool, 10, uuid.uuid4(), "like")
        assert ok is True

    @pytest.mark.asyncio
    async def test_returns_false_when_not_owned_or_missing(self, fake_pool):
        fake_pool.fetchrow.return_value = None
        ok = await feedback_q.registrar_feedback(
            fake_pool, 10, uuid.uuid4(), "dislike", "Informação incorreta", "errou o partido"
        )
        assert ok is False

    @pytest.mark.asyncio
    async def test_passes_optional_details_as_params(self, fake_pool):
        fake_pool.fetchrow.return_value = record(id=2)
        await feedback_q.registrar_feedback(
            fake_pool, 7, uuid.uuid4(), "dislike", "Link ou fonte incorreta", "link errado"
        )
        args = fake_pool.fetchrow.call_args.args
        # ($1 query, mensagem_id, user_id, tipo, categoria, comentario)
        assert args[1] == 7
        assert args[3] == "dislike"
        assert args[4] == "Link ou fonte incorreta"
        assert args[5] == "link errado"


class TestUltimosFeedbacks:
    @pytest.mark.asyncio
    async def test_maps_message_id_to_latest_tipo(self, fake_pool):
        fake_pool.fetch.return_value = [
            record(mensagem_id=1, tipo="like"),
            record(mensagem_id=2, tipo="dislike"),
        ]
        out = await feedback_q.ultimos_feedbacks(fake_pool, uuid.uuid4(), uuid.uuid4())
        assert out == {1: "like", 2: "dislike"}

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


class TestBuscarConversaDegradesOnFeedbackFailure:
    @pytest.mark.asyncio
    async def test_conversation_loads_when_feedback_query_raises(self, fake_pool, monkeypatch):
        """A broken feedback lookup must not 500 the whole conversation load."""
        from app.routers import chats

        conversa_id = uuid.uuid4()
        now = datetime.now()
        monkeypatch.setattr(chats, "get_pool", lambda: fake_pool)

        async def fake_buscar(pool, cid, user_id=None):
            return {
                "id": cid,
                "titulo": "t",
                "created_at": now,
                "updated_at": now,
                "mensagens": [{"id": 1, "role": "assistant", "content": "oi", "tool_calls": None}],
            }

        async def boom(pool, cid, user_id):
            raise RuntimeError("relation mensagem_feedback does not exist")

        monkeypatch.setattr(chats.conversas_q, "buscar_conversa", fake_buscar)
        monkeypatch.setattr(chats.feedback_q, "ultimos_feedbacks", boom)

        result = await chats.buscar_conversa(
            conversa_id=conversa_id, current_user={"id": str(uuid.uuid4())}
        )
        assert result.mensagens[0].feedback is None
        assert result.mensagens[0].content == "oi"
