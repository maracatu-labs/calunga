import uuid

import asyncpg

async def criar_magic_link(pool: asyncpg.Pool, email: str) -> uuid.UUID:
    row = await pool.fetchrow(
        "INSERT INTO magic_links (email) VALUES ($1) RETURNING id",
        email,
    )
    return row["id"]

async def validar_magic_link(pool: asyncpg.Pool, token_id: uuid.UUID) -> str | None:
    """Retorna o email se o token é válido (não expirado, não usado). None caso contrário."""
    row = await pool.fetchrow(
        """
        SELECT email FROM magic_links
        WHERE id = $1 AND used = FALSE AND expires_at > NOW()
        """,
        token_id,
    )
    return row["email"] if row else None

async def marcar_magic_link_usado(pool: asyncpg.Pool, token_id: uuid.UUID) -> None:
    await pool.execute(
        "UPDATE magic_links SET used = TRUE WHERE id = $1",
        token_id,
    )

async def buscar_ou_criar_user(pool: asyncpg.Pool, email: str) -> dict:
    """Busca user por email ou cria um novo. Retorna {id, email}."""
    row = await pool.fetchrow(
        "SELECT id, email FROM users WHERE email = $1",
        email,
    )
    if row:
        return dict(row)

    row = await pool.fetchrow(
        "INSERT INTO users (email) VALUES ($1) RETURNING id, email",
        email,
    )
    return dict(row)

async def buscar_user_por_id(pool: asyncpg.Pool, user_id: uuid.UUID) -> dict | None:
    row = await pool.fetchrow(
        "SELECT id, email FROM users WHERE id = $1",
        user_id,
    )
    return dict(row) if row else None
