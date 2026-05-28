import asyncpg


async def buscar_empresa_por_cnpj(pool: asyncpg.Pool, cnpj: str) -> asyncpg.Record | None:
    digits = cnpj.replace(".", "").replace("/", "").replace("-", "").strip()
    return await pool.fetchrow(
        "SELECT * FROM empresas WHERE cnpj = $1",
        digits,
    )

async def empresa_tem_sancao(pool: asyncpg.Pool, cnpj: str) -> list[asyncpg.Record]:
    digits = cnpj.replace(".", "").replace("/", "").replace("-", "").strip()
    return await pool.fetch(
        "SELECT * FROM sancoes WHERE cpf_cnpj = $1",
        digits,
    )
