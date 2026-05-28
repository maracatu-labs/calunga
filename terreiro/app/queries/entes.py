import asyncpg


async def listar_entes(
    pool: asyncpg.Pool,
    *,
    tipo: str | None = None,
    uf: str | None = None,
    capital: bool | None = None,
) -> list[asyncpg.Record]:
    query = "SELECT * FROM entes WHERE 1=1"
    params: list = []

    if tipo:
        params.append(tipo)
        query += f" AND tipo = ${len(params)}"

    if uf:
        params.append(uf.upper())
        query += f" AND uf = ${len(params)}"

    if capital is not None:
        params.append(capital)
        query += f" AND capital = ${len(params)}"

    query += " ORDER BY nome"
    return await pool.fetch(query, *params)

async def buscar_ente_por_ibge(pool: asyncpg.Pool, ibge_codigo: str) -> asyncpg.Record | None:
    return await pool.fetchrow("SELECT * FROM entes WHERE ibge_codigo = $1", ibge_codigo)

async def buscar_ente(pool: asyncpg.Pool, ente_id: int) -> asyncpg.Record | None:
    return await pool.fetchrow("SELECT * FROM entes WHERE id = $1", ente_id)
