import json
import uuid
from typing import Any

import asyncpg


def _decode_messages(rows: list[asyncpg.Record]) -> list[dict]:
    """Turn message rows into dicts, decoding the tool_calls JSONB column.

    asyncpg returns jsonb as a raw string (no codec is registered on the pool),
    so we json.loads it back into a list the API can serialize.
    """
    out = []
    for row in rows:
        msg = dict(row)
        raw = msg.get("tool_calls")
        if isinstance(raw, str):
            try:
                msg["tool_calls"] = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                msg["tool_calls"] = None
        out.append(msg)
    return out


async def criar_conversa(
    pool: asyncpg.Pool, titulo: str | None = None, user_id: uuid.UUID | None = None
) -> uuid.UUID:
    row = await pool.fetchrow(
        "INSERT INTO conversas (titulo, user_id) VALUES ($1, $2) RETURNING id",
        titulo,
        user_id,
    )
    return row["id"]

async def listar_conversas(
    pool: asyncpg.Pool,
    *,
    user_id: uuid.UUID | None = None,
    limit: int = 30,
    offset: int = 0,
) -> list[asyncpg.Record]:
    if user_id:
        return await pool.fetch(
            """
            SELECT c.id, c.titulo, c.created_at, c.updated_at,
                   (SELECT content FROM mensagens WHERE conversa_id = c.id ORDER BY created_at DESC LIMIT 1) AS ultima_mensagem
            FROM conversas c
            WHERE c.user_id = $1
            ORDER BY c.updated_at DESC
            LIMIT $2 OFFSET $3
            """,
            user_id,
            limit,
            offset,
        )
    return await pool.fetch(
        """
        SELECT c.id, c.titulo, c.created_at, c.updated_at,
               (SELECT content FROM mensagens WHERE conversa_id = c.id ORDER BY created_at DESC LIMIT 1) AS ultima_mensagem
        FROM conversas c
        ORDER BY c.updated_at DESC
        LIMIT $1 OFFSET $2
        """,
        limit,
        offset,
    )

async def buscar_conversa(
    pool: asyncpg.Pool, conversa_id: uuid.UUID, user_id: uuid.UUID | None = None
) -> dict | None:
    if user_id:
        conversa = await pool.fetchrow(
            "SELECT * FROM conversas WHERE id = $1 AND user_id = $2",
            conversa_id,
            user_id,
        )
    else:
        conversa = await pool.fetchrow(
            "SELECT * FROM conversas WHERE id = $1",
            conversa_id,
        )
    if not conversa:
        return None

    mensagens = await pool.fetch(
        "SELECT id, role, content, tool_calls, created_at FROM mensagens WHERE conversa_id = $1 ORDER BY created_at",
        conversa_id,
    )

    return {
        "id": conversa["id"],
        "titulo": conversa["titulo"],
        "created_at": conversa["created_at"],
        "updated_at": conversa["updated_at"],
        "mensagens": _decode_messages(mensagens),
    }

async def adicionar_mensagem(
    pool: asyncpg.Pool,
    conversa_id: uuid.UUID,
    role: str,
    content: str,
    tool_calls: list[Any] | None = None,
) -> asyncpg.Record:
    row = await pool.fetchrow(
        """
        INSERT INTO mensagens (conversa_id, role, content, tool_calls)
        VALUES ($1, $2, $3, $4::jsonb)
        RETURNING *
        """,
        conversa_id,
        role,
        content,
        json.dumps(tool_calls) if tool_calls else None,
    )
    await pool.execute(
        "UPDATE conversas SET updated_at = NOW() WHERE id = $1",
        conversa_id,
    )
    return row

async def atualizar_titulo(pool: asyncpg.Pool, conversa_id: uuid.UUID, titulo: str) -> None:
    await pool.execute(
        "UPDATE conversas SET titulo = $1, updated_at = NOW() WHERE id = $2",
        titulo,
        conversa_id,
    )

async def compartilhar_conversa(
    pool: asyncpg.Pool, conversa_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    result = await pool.execute(
        "UPDATE conversas SET shared = TRUE WHERE id = $1 AND user_id = $2",
        conversa_id,
        user_id,
    )
    return result == "UPDATE 1"

async def buscar_conversa_publica(pool: asyncpg.Pool, conversa_id: uuid.UUID) -> dict | None:
    conversa = await pool.fetchrow(
        "SELECT * FROM conversas WHERE id = $1 AND shared = TRUE",
        conversa_id,
    )
    if not conversa:
        return None

    mensagens = await pool.fetch(
        "SELECT id, role, content, tool_calls, created_at FROM mensagens WHERE conversa_id = $1 ORDER BY created_at",
        conversa_id,
    )

    return {
        "id": conversa["id"],
        "titulo": conversa["titulo"],
        "created_at": conversa["created_at"],
        "updated_at": conversa["updated_at"],
        "mensagens": _decode_messages(mensagens),
    }

async def deletar_conversa(
    pool: asyncpg.Pool, conversa_id: uuid.UUID, user_id: uuid.UUID | None = None
) -> bool:
    if user_id:
        result = await pool.execute(
            "DELETE FROM conversas WHERE id = $1 AND user_id = $2",
            conversa_id,
            user_id,
        )
    else:
        result = await pool.execute(
            "DELETE FROM conversas WHERE id = $1",
            conversa_id,
        )
    return result == "DELETE 1"

async def deletar_todas_conversas(pool: asyncpg.Pool, user_id: uuid.UUID) -> int:
    """Delete every conversation for the given user. Returns count deleted.

    Messages cascade automatically via the mensagens.conversa_id foreign key
    (ON DELETE CASCADE in migration 0001).
    """
    result = await pool.execute(
        "DELETE FROM conversas WHERE user_id = $1",
        user_id,
    )
    # asyncpg returns the command tag, e.g. "DELETE 7"
    parts = result.split()
    return int(parts[1]) if len(parts) == 2 and parts[0] == "DELETE" else 0
