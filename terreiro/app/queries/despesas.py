import asyncpg

from app.sanitize import (
    limpar_documento,
    normalizar_ano,
    normalizar_data,
    normalizar_mes,
    normalizar_texto,
    normalizar_valor,
    normalizar_valor_positivo,
    to_int,
)

async def listar_despesas(
    pool: asyncpg.Pool,
    *,
    parlamentar_id: int | None = None,
    ano: int | None = None,
    mes: int | None = None,
    categoria: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[asyncpg.Record]:
    query = """
        SELECT d.*, p.nome AS parlamentar_nome, p.partido, p.uf
        FROM despesas d
        JOIN parlamentares p ON d.parlamentar_id = p.id
        WHERE 1=1
    """
    params: list = []

    if parlamentar_id:
        params.append(parlamentar_id)
        query += f" AND d.parlamentar_id = ${len(params)}"

    if ano:
        params.append(ano)
        query += f" AND d.ano = ${len(params)}"

    if mes:
        params.append(mes)
        query += f" AND d.mes = ${len(params)}"

    if categoria:
        params.append(f"%{categoria}%")
        query += f" AND d.categoria ILIKE ${len(params)}"

    query += " ORDER BY d.data_emissao DESC NULLS LAST, d.id DESC"

    params.append(limit)
    query += f" LIMIT ${len(params)}"

    params.append(offset)
    query += f" OFFSET ${len(params)}"

    return await pool.fetch(query, *params)

async def buscar_despesas_por_nome(
    pool: asyncpg.Pool,
    nome: str,
    *,
    ano: int | None = None,
    mes: int | None = None,
    categoria: str | None = None,
    limit: int = 50,
) -> list[asyncpg.Record]:
    query = """
        SELECT d.*, p.nome AS parlamentar_nome, p.partido, p.uf
        FROM despesas d
        JOIN parlamentares p ON d.parlamentar_id = p.id
        WHERE p.nome ILIKE $1
    """
    params: list = [f"%{nome}%"]

    if ano:
        params.append(ano)
        query += f" AND d.ano = ${len(params)}"

    if mes:
        params.append(mes)
        query += f" AND d.mes = ${len(params)}"

    if categoria:
        params.append(f"%{categoria}%")
        query += f" AND d.categoria ILIKE ${len(params)}"

    query += " ORDER BY d.data_emissao DESC NULLS LAST"

    params.append(limit)
    query += f" LIMIT ${len(params)}"

    return await pool.fetch(query, *params)

async def resumo_despesas_por_categoria(
    pool: asyncpg.Pool,
    parlamentar_id: int,
    *,
    ano: int | None = None,
) -> list[asyncpg.Record]:
    query = """
        SELECT
            d.categoria,
            COUNT(*) AS total_registros,
            SUM(d.valor_liquido) AS valor_total,
            AVG(d.valor_liquido) AS valor_medio
        FROM despesas d
        WHERE d.parlamentar_id = $1
    """
    params: list = [parlamentar_id]

    if ano:
        params.append(ano)
        query += f" AND d.ano = ${len(params)}"

    query += " GROUP BY d.categoria ORDER BY valor_total DESC"

    return await pool.fetch(query, *params)

async def resumo_despesas(
    pool: asyncpg.Pool,
    *,
    nome: str | None = None,
    parlamentar_id: int | None = None,
    ano: int | None = None,
    mes: int | None = None,
    categoria: str | None = None,
) -> dict | None:
    """Retorna resumo agregado de despesas (total, por categoria, por mês, top 5)."""
    where = "WHERE 1=1"
    params: list = []

    if nome:
        params.append(f"%{nome}%")
        where += f" AND p.nome ILIKE ${len(params)}"
    elif parlamentar_id:
        params.append(parlamentar_id)
        where += f" AND d.parlamentar_id = ${len(params)}"

    if ano:
        params.append(ano)
        where += f" AND d.ano = ${len(params)}"
    if mes:
        params.append(mes)
        where += f" AND d.mes = ${len(params)}"
    if categoria:
        params.append(f"%{categoria}%")
        where += f" AND d.categoria ILIKE ${len(params)}"

    row = await pool.fetchrow(
        f"""
        SELECT p.nome, p.partido, p.uf, p.tipo,
               COUNT(*) AS total_registros,
               SUM(d.valor_liquido) AS valor_total
        FROM despesas d
        JOIN parlamentares p ON d.parlamentar_id = p.id
        {where}
        GROUP BY p.nome, p.partido, p.uf, p.tipo
        ORDER BY valor_total DESC
        LIMIT 1
        """,
        *params,
    )
    if not row or row["total_registros"] == 0:
        return None

    categorias = await pool.fetch(
        f"""
        SELECT d.categoria, COUNT(*) AS total, SUM(d.valor_liquido) AS valor
        FROM despesas d
        JOIN parlamentares p ON d.parlamentar_id = p.id
        {where}
        GROUP BY d.categoria ORDER BY valor DESC
        """,
        *params,
    )

    meses = await pool.fetch(
        f"""
        SELECT d.mes, SUM(d.valor_liquido) AS valor
        FROM despesas d
        JOIN parlamentares p ON d.parlamentar_id = p.id
        {where}
        GROUP BY d.mes ORDER BY d.mes
        """,
        *params,
    )

    top5 = await pool.fetch(
        f"""
        SELECT d.fornecedor, d.categoria, d.valor_liquido, d.data_emissao
        FROM despesas d
        JOIN parlamentares p ON d.parlamentar_id = p.id
        {where}
        ORDER BY d.valor_liquido DESC NULLS LAST
        LIMIT 5
        """,
        *params,
    )

    return {
        "nome": row["nome"],
        "tipo": row["tipo"],
        "partido": row["partido"],
        "uf": row["uf"],
        "total_registros": row["total_registros"],
        "valor_total": row["valor_total"],
        "categorias": [dict(c) for c in categorias],
        "meses": [dict(m) for m in meses],
        "top5": [dict(t) for t in top5],
    }

async def ranking_deputados_por_gasto(
    pool: asyncpg.Pool,
    *,
    tipo: str | None = None,
    ano: int | None = None,
    categoria: str | None = None,
    uf: str | None = None,
    partido: str | None = None,
    limit: int = 10,
) -> list[asyncpg.Record]:
    query = """
        SELECT
            p.nome,
            p.tipo,
            p.partido,
            p.uf,
            COUNT(*) AS total_registros,
            SUM(d.valor_liquido) AS valor_total
        FROM despesas d
        JOIN parlamentares p ON d.parlamentar_id = p.id
        WHERE 1=1
    """
    params: list = []

    if tipo:
        params.append(tipo)
        query += f" AND p.tipo = ${len(params)}"

    if ano:
        params.append(ano)
        query += f" AND d.ano = ${len(params)}"

    if categoria:
        params.append(f"%{categoria}%")
        query += f" AND d.categoria ILIKE ${len(params)}"

    if uf:
        params.append(uf.upper())
        query += f" AND p.uf = ${len(params)}"

    if partido:
        params.append(partido.upper())
        query += f" AND p.partido = ${len(params)}"

    query += " GROUP BY p.nome, p.tipo, p.partido, p.uf ORDER BY valor_total DESC"

    params.append(limit)
    query += f" LIMIT ${len(params)}"

    return await pool.fetch(query, *params)

async def upsert_despesa(pool: asyncpg.Pool, **data) -> asyncpg.Record:

    data_emissao = data.get("data_emissao")
    if isinstance(data_emissao, str):
        data_emissao = normalizar_data(data_emissao)

    return await pool.fetchrow(
        """
        INSERT INTO despesas (id_externo, parlamentar_id, ano, mes, data_emissao, categoria,
                              subcategoria, fornecedor, cnpj_cpf, documento, valor_documento,
                              valor_glosa, valor_liquido, url_documento, lote, ressarcimento)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
        ON CONFLICT (id_externo)
        DO UPDATE SET
            valor_documento = EXCLUDED.valor_documento,
            valor_glosa = EXCLUDED.valor_glosa,
            valor_liquido = EXCLUDED.valor_liquido,
            url_documento = EXCLUDED.url_documento
        RETURNING *
        """,
        normalizar_texto(data.get("id_externo"), max_len=200),
        data.get("parlamentar_id"),
        normalizar_ano(data.get("ano")),
        normalizar_mes(data.get("mes")),
        data_emissao,
        normalizar_texto(data.get("categoria")) or "Não informado",
        normalizar_texto(data.get("subcategoria")),
        normalizar_texto(data.get("fornecedor"), max_len=200),
        limpar_documento(data.get("cnpj_cpf")),
        normalizar_texto(data.get("documento"), max_len=200),
        normalizar_valor(data.get("valor_documento")),
        normalizar_valor_positivo(data.get("valor_glosa"), default=0),
        normalizar_valor(data.get("valor_liquido")),
        normalizar_texto(data.get("url_documento")),
        to_int(data.get("lote")),
        to_int(data.get("ressarcimento")),
    )
