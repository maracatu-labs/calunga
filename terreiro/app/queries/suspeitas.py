import asyncpg


async def listar_suspeitas(
    pool: asyncpg.Pool,
    *,
    parlamentar_nome: str | None = None,
    classificador: str | None = None,
    ano: int | None = None,
    limit: int = 20,
) -> list[asyncpg.Record]:
    query = """
        SELECT s.id, s.despesa_id, s.classificador, s.probabilidade, s.detalhes, s.created_at,
               d.categoria, d.fornecedor, d.valor_liquido, d.ano, d.mes, d.data_emissao, d.cnpj_cpf,
               p.nome AS parlamentar_nome, p.partido, p.uf,
               p.id_externo AS parlamentar_id_externo, p.tipo AS parlamentar_tipo
        FROM suspeitas s
        JOIN despesas d ON s.despesa_id = d.id
        JOIN parlamentares p ON d.parlamentar_id = p.id
        WHERE 1=1
    """
    params: list = []

    if parlamentar_nome:
        params.append(f"%{parlamentar_nome}%")
        query += f" AND p.nome ILIKE ${len(params)}"

    if classificador:
        params.append(classificador)
        query += f" AND s.classificador = ${len(params)}"

    if ano:
        params.append(ano)
        query += f" AND d.ano = ${len(params)}"

    query += " ORDER BY s.probabilidade DESC, d.valor_liquido DESC"

    params.append(limit)
    query += f" LIMIT ${len(params)}"

    return await pool.fetch(query, *params)

async def contar_suspeitas_por_classificador(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    return await pool.fetch(
        """
        SELECT s.classificador, COUNT(*) AS total, AVG(s.probabilidade) AS prob_media
        FROM suspeitas s
        GROUP BY s.classificador
        ORDER BY total DESC
        """
    )
