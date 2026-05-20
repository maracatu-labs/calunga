"""Busca híbrida: full-text (BM25) + vetorial (cosine similarity) em múltiplas tabelas."""

import json

import asyncpg

async def busca_hibrida(
    pool: asyncpg.Pool,
    query_text: str,
    query_embedding: list[float] | None = None,
    *,
    limit: int = 10,
    peso_dense: float = 0.7,
    peso_sparse: float = 0.3,
) -> list[asyncpg.Record]:
    """Busca híbrida combinando full-text search + similaridade vetorial em despesas."""

    if query_embedding:
        return await pool.fetch(
            """
            WITH fts AS (
                SELECT d.id, ts_rank(d.search_vector, websearch_to_tsquery('portuguese', $1)) AS fts_score
                FROM despesas d
                WHERE d.search_vector @@ websearch_to_tsquery('portuguese', $1)
            ),
            vec AS (
                SELECT e.referencia_id AS id, 1 - (e.embedding <=> $2::vector) AS vec_score
                FROM embeddings e
                WHERE e.tipo = 'despesa'
                ORDER BY e.embedding <=> $2::vector
                LIMIT 50
            ),
            combined AS (
                SELECT COALESCE(fts.id, vec.id) AS id,
                       ($3 * COALESCE(vec.vec_score, 0)) + ($4 * COALESCE(fts.fts_score, 0)) AS score
                FROM fts
                FULL OUTER JOIN vec ON fts.id = vec.id
            )
            SELECT d.*, p.nome AS parlamentar_nome, p.partido, p.uf, c.score
            FROM combined c
            JOIN despesas d ON d.id = c.id
            JOIN parlamentares p ON d.parlamentar_id = p.id
            ORDER BY c.score DESC
            LIMIT $5
            """,
            query_text,
            json.dumps(query_embedding),
            peso_dense,
            peso_sparse,
            limit,
        )
    else:
        return await pool.fetch(
            """
            SELECT d.*, p.nome AS parlamentar_nome, p.partido, p.uf,
                   ts_rank(d.search_vector, websearch_to_tsquery('portuguese', $1)) AS score
            FROM despesas d
            JOIN parlamentares p ON d.parlamentar_id = p.id
            WHERE d.search_vector @@ websearch_to_tsquery('portuguese', $1)
            ORDER BY score DESC
            LIMIT $2
            """,
            query_text,
            limit,
        )

async def busca_universal(
    pool: asyncpg.Pool,
    query_text: str,
    query_embedding: list[float] | None = None,
    *,
    limit: int = 15,
) -> list[dict]:
    """Busca semântica em todas as tabelas com embeddings.
    Retorna resultados rankeados por relevância com tipo e dados formatados."""

    if not query_embedding:
        return []

    embedding_json = json.dumps(query_embedding)

    rows = await pool.fetch(
        """
        SELECT e.tipo, e.referencia_id, e.conteudo_texto,
               1 - (e.embedding <=> $1::vector) AS score
        FROM embeddings e
        ORDER BY e.embedding <=> $1::vector
        LIMIT $2
        """,
        embedding_json,
        limit * 2,
    )

    results = []
    for r in rows:
        tipo = r["tipo"]
        ref_id = r["referencia_id"]
        item = {
            "tipo": tipo,
            "resumo": r["conteudo_texto"][:300],
            "relevancia": round(float(r["score"]), 4),
        }

        if tipo == "despesa":
            detail = await pool.fetchrow(
                """SELECT d.*, p.nome AS parlamentar_nome, p.partido, p.uf
                FROM despesas d JOIN parlamentares p ON d.parlamentar_id = p.id
                WHERE d.id = $1""", ref_id
            )
            if detail:
                item["parlamentar"] = detail["parlamentar_nome"]
                item["partido"] = detail["partido"]
                item["uf"] = detail["uf"]
                item["categoria"] = detail["categoria"]
                item["fornecedor"] = detail["fornecedor"]
                item["valor"] = str(detail["valor_liquido"]) if detail["valor_liquido"] else None
                item["ano"] = detail["ano"]

        elif tipo == "contrato":
            detail = await pool.fetchrow("SELECT * FROM contratos WHERE id = $1", ref_id)
            if detail:
                item["orgao"] = detail["orgao_nome"]
                item["fornecedor"] = detail["fornecedor_nome"]
                item["objeto"] = (detail["objeto"] or "")[:200]
                item["valor"] = str(detail["valor_final"]) if detail["valor_final"] else None
                item["situacao"] = detail["situacao"]

        elif tipo == "licitacao":
            detail = await pool.fetchrow("SELECT * FROM licitacoes WHERE id = $1", ref_id)
            if detail:
                item["orgao"] = detail["orgao_nome"]
                item["objeto"] = (detail["objeto"] or "")[:200]
                item["modalidade"] = detail["modalidade"]
                item["situacao"] = detail["situacao"]
                item["valor"] = str(detail["valor_estimado"]) if detail["valor_estimado"] else None

        elif tipo == "emenda":
            detail = await pool.fetchrow("SELECT * FROM emendas WHERE id = $1", ref_id)
            if detail:
                item["autor"] = detail["autor"]
                item["tipo_emenda"] = detail["tipo_emenda"]
                item["localidade"] = detail["localidade_gasto"]
                item["funcao"] = detail["funcao"]
                item["valor_empenhado"] = str(detail["valor_empenhado"]) if detail["valor_empenhado"] else None
                item["ano"] = detail["ano"]

        elif tipo == "proposicao":
            detail = await pool.fetchrow("SELECT * FROM proposicoes WHERE id = $1", ref_id)
            if detail:
                item["sigla"] = f"{detail['sigla_tipo']} {detail['numero']}/{detail['ano']}"
                item["casa"] = detail["casa"]
                item["ementa"] = (detail["ementa"] or "")[:300]
                item["autor"] = detail["autor"]

        elif tipo == "votacao":
            detail = await pool.fetchrow(
                """SELECT v.*, p.ementa AS proposicao_ementa
                FROM votacoes v LEFT JOIN proposicoes p ON v.proposicao_id = p.id
                WHERE v.id = $1""", ref_id
            )
            if detail:
                item["casa"] = detail["casa"]
                item["proposicao"] = f"{detail['sigla_tipo']} {detail['numero']}/{detail['ano']}" if detail["sigla_tipo"] else None
                item["aprovada"] = detail["aprovada"]
                item["votos_sim"] = detail["votos_sim"]
                item["votos_nao"] = detail["votos_nao"]
                item["ementa"] = (detail["proposicao_ementa"] or "")[:200]
                item["data"] = str(detail["data_hora"].date()) if detail["data_hora"] else None

        elif tipo == "viagem":
            detail = await pool.fetchrow("SELECT * FROM viagens WHERE id = $1", ref_id)
            if detail:
                item["orgao"] = detail["orgao_nome"]
                item["viajante"] = detail["viajante_nome"]
                item["cargo"] = detail["cargo"]
                item["destino"] = detail["destino"]
                item["motivo"] = (detail["motivo"] or "")[:200]
                item["urgente"] = detail["urgente"]
                item["valor_passagens"] = str(detail["valor_passagens"]) if detail["valor_passagens"] else None
                item["valor_diarias"] = str(detail["valor_diarias"]) if detail["valor_diarias"] else None
                item["data"] = str(detail["data_ida"]) if detail["data_ida"] else None

        elif tipo == "cpgf":
            detail = await pool.fetchrow("SELECT * FROM cpgf WHERE id = $1", ref_id)
            if detail:
                item["orgao"] = detail["orgao_nome"]
                item["portador"] = detail["portador_nome"]
                item["favorecido"] = detail["favorecido_nome"]
                item["valor"] = str(detail["valor"]) if detail["valor"] else None
                item["data"] = str(detail["data_transacao"]) if detail["data_transacao"] else None

        elif tipo == "sancao":
            detail = await pool.fetchrow("SELECT * FROM sancoes WHERE id = $1", ref_id)
            if detail:
                item["tipo_sancao"] = detail["tipo"]
                item["nome"] = detail["nome"]
                item["cpf_cnpj"] = detail["cpf_cnpj"]
                item["orgao_sancionador"] = detail["orgao_sancionador"]
                item["fundamentacao"] = (detail["fundamentacao_legal"] or "")[:200]
                item["data_inicio"] = str(detail["data_inicio"]) if detail["data_inicio"] else None
                item["data_fim"] = str(detail["data_fim"]) if detail["data_fim"] else None

        results.append(item)

    results.sort(key=lambda x: x["relevancia"], reverse=True)
    return results[:limit]
