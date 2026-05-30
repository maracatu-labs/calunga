import uuid

import asyncpg


async def registrar_feedback(
    pool: asyncpg.Pool,
    mensagem_id: int,
    user_id: uuid.UUID,
    tipo: str,
    categoria: str | None = None,
    comentario: str | None = None,
) -> bool:
    """Append a feedback record for an assistant message owned by the user.

    Ownership-guarded via INSERT ... SELECT: the row is only inserted when the
    message exists, has role 'assistant', and belongs to a conversation owned by
    this user. Append-only — no unique constraint, so every call adds a record.
    `categoria` and `comentario` are optional details from the feedback modal.
    Returns True if a row was inserted, False otherwise (missing message, not the
    user's, or not an assistant message).
    """
    row = await pool.fetchrow(
        """
        INSERT INTO mensagem_feedback (mensagem_id, user_id, tipo, categoria, comentario)
        SELECT m.id, $2, $3, $4, $5
        FROM mensagens m
        JOIN conversas c ON c.id = m.conversa_id
        WHERE m.id = $1 AND c.user_id = $2 AND m.role = 'assistant'
        RETURNING id
        """,
        mensagem_id,
        user_id,
        tipo,
        categoria,
        comentario,
    )
    return row is not None


async def ultimos_feedbacks(
    pool: asyncpg.Pool, conversa_id: uuid.UUID, user_id: uuid.UUID
) -> dict[int, str]:
    """Return the most recent feedback type per message for a user in a conversation.

    Used to hydrate the UI state on reload. Maps mensagem_id -> tipo, picking the
    latest record per message via DISTINCT ON.
    """
    rows = await pool.fetch(
        """
        SELECT DISTINCT ON (mf.mensagem_id) mf.mensagem_id, mf.tipo
        FROM mensagem_feedback mf
        JOIN mensagens m ON m.id = mf.mensagem_id
        WHERE m.conversa_id = $1 AND mf.user_id = $2
        ORDER BY mf.mensagem_id, mf.created_at DESC
        """,
        conversa_id,
        user_id,
    )
    return {row["mensagem_id"]: row["tipo"] for row in rows}
