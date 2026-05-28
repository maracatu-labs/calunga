import uuid

import asyncpg


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
        "SELECT id, role, content, created_at FROM mensagens WHERE conversa_id = $1 ORDER BY created_at",
        conversa_id,
    )

    return {
        "id": conversa["id"],
        "titulo": conversa["titulo"],
        "created_at": conversa["created_at"],
        "updated_at": conversa["updated_at"],
        "mensagens": [dict(m) for m in mensagens],
    }

async def adicionar_mensagem(
    pool: asyncpg.Pool, conversa_id: uuid.UUID, role: str, content: str
) -> asyncpg.Record:
    row = await pool.fetchrow(
        """
        INSERT INTO mensagens (conversa_id, role, content)
        VALUES ($1, $2, $3)
        RETURNING *
        """,
        conversa_id,
        role,
        content,
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
        "SELECT id, role, content, created_at FROM mensagens WHERE conversa_id = $1 ORDER BY created_at",
        conversa_id,
    )

    return {
        "id": conversa["id"],
        "titulo": conversa["titulo"],
        "created_at": conversa["created_at"],
        "updated_at": conversa["updated_at"],
        "mensagens": [dict(m) for m in mensagens],
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
