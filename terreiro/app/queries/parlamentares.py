import uuid

import asyncpg

from app.sanitize import (
    normalizar_email,
    normalizar_nome,
    normalizar_partido,
    normalizar_texto,
    normalizar_uf,
)


async def listar_parlamentares(
    pool: asyncpg.Pool,
    *,
    tipo: str | None = None,
    uf: str | None = None,
    partido: str | None = None,
    nome: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[asyncpg.Record]:
    query = "SELECT * FROM parlamentares WHERE 1=1"
    params: list = []

    if tipo:
        params.append(tipo)
        query += f" AND tipo = ${len(params)}"

    if uf:
        params.append(uf.upper())
        query += f" AND uf = ${len(params)}"

    if partido:
        params.append(partido.upper())
        query += f" AND partido = ${len(params)}"

    if nome:
        params.append(f"%{nome}%")
        query += f" AND nome ILIKE ${len(params)}"

    query += " ORDER BY nome"

    params.append(limit)
    query += f" LIMIT ${len(params)}"

    params.append(offset)
    query += f" OFFSET ${len(params)}"

    return await pool.fetch(query, *params)

async def buscar_parlamentar(pool: asyncpg.Pool, parlamentar_id: uuid.UUID) -> asyncpg.Record | None:
    return await pool.fetchrow(
        "SELECT * FROM parlamentares WHERE id = $1",
        parlamentar_id,
    )

async def buscar_parlamentar_por_id_externo(
    pool: asyncpg.Pool, id_externo: str
) -> asyncpg.Record | None:
    return await pool.fetchrow(
        "SELECT * FROM parlamentares WHERE id_externo = $1",
        id_externo,
    )

async def upsert_parlamentar(pool: asyncpg.Pool, **data) -> asyncpg.Record:
    return await pool.fetchrow(
        """
        INSERT INTO parlamentares (id_externo, tipo, nome, nome_civil, cpf, partido, uf,
                                   legislatura, foto_url, email, telefone, situacao,
                                   esfera, ente_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        ON CONFLICT (id_externo)
        DO UPDATE SET
            nome = EXCLUDED.nome,
            partido = EXCLUDED.partido,
            uf = EXCLUDED.uf,
            legislatura = EXCLUDED.legislatura,
            foto_url = EXCLUDED.foto_url,
            email = EXCLUDED.email,
            telefone = EXCLUDED.telefone,
            situacao = EXCLUDED.situacao,
            esfera = COALESCE(EXCLUDED.esfera, parlamentares.esfera),
            ente_id = COALESCE(EXCLUDED.ente_id, parlamentares.ente_id),
            updated_at = NOW()
        RETURNING *
        """,
        normalizar_texto(data.get("id_externo"), max_len=20),
        data.get("tipo", "deputado"),
        normalizar_nome(data.get("nome")),
        normalizar_nome(data.get("nome_civil")),
        data.get("cpf"),
        normalizar_partido(data.get("partido")),
        normalizar_uf(data.get("uf")),
        data.get("legislatura"),
        normalizar_texto(data.get("foto_url")),
        normalizar_email(data.get("email")),
        normalizar_texto(data.get("telefone"), max_len=20),
        normalizar_texto(data.get("situacao"), max_len=50),
        data.get("esfera"),
        data.get("ente_id"),
    )
