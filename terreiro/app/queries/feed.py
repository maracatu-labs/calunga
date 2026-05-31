"""Queries para o feed público de eventos."""

import json
import uuid

import asyncpg

from app.sanitize import normalizar_texto


async def publicar_evento(pool: asyncpg.Pool, **data) -> asyncpg.Record | None:
    """Publica evento no feed. Ignora se já existe (mesmo referencia_tipo + referencia_id + tipo)."""
    return await pool.fetchrow(
        """
        INSERT INTO feed_eventos (tipo, categoria, origem, titulo, descricao, dados,
                                  referencia_tipo, referencia_id, relevancia)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9)
        ON CONFLICT (referencia_tipo, referencia_id, tipo) DO NOTHING
        RETURNING *
        """,
        normalizar_texto(data.get("tipo"), max_len=50),
        normalizar_texto(data.get("categoria"), max_len=50),
        data.get("origem", "dagster"),
        normalizar_texto(data.get("titulo")),
        normalizar_texto(data.get("descricao")),
        json.dumps(data.get("dados") or {}, ensure_ascii=False, default=str),
        normalizar_texto(data.get("referencia_tipo"), max_len=50),
        data.get("referencia_id"),
        data.get("relevancia", 0.5),
    )

def _build_filters(
    tipo: str | None,
    categoria: str | None,
    origem: str | None,
) -> tuple[str, list]:
    clauses: list[str] = []
    params: list = []
    if tipo:
        params.append(tipo)
        clauses.append(f"tipo = ${len(params)}")
    if categoria:
        params.append(categoria)
        clauses.append(f"categoria = ${len(params)}")
    if origem:
        params.append(origem)
        clauses.append(f"origem = ${len(params)}")
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params

async def listar_feed(
    pool: asyncpg.Pool,
    *,
    tipo: str | None = None,
    categoria: str | None = None,
    origem: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[asyncpg.Record]:
    """Lista eventos do feed ordenados por score decaindo no tempo.

    score = relevancia * exp(-dias_desde_criacao / 7)
    Eventos recentes e relevantes aparecem no topo; eventos antigos decaem
    mesmo com alta relevância. Empate resolvido por created_at desc.
    """
    where, params = _build_filters(tipo, categoria, origem)

    params.append(limit)
    limit_ph = f"${len(params)}"
    params.append(offset)
    offset_ph = f"${len(params)}"

    query = f"""
        SELECT
            *,
            relevancia * exp(
                -EXTRACT(EPOCH FROM (NOW() - created_at)) / 604800.0
            ) AS score
        FROM feed_eventos
        {where}
        ORDER BY score DESC, created_at DESC
        LIMIT {limit_ph} OFFSET {offset_ph}
    """
    return await pool.fetch(query, *params)

async def contar_feed(
    pool: asyncpg.Pool,
    *,
    tipo: str | None = None,
    categoria: str | None = None,
    origem: str | None = None,
) -> int:
    """Conta eventos do feed aplicando os mesmos filtros de listar_feed."""
    where, params = _build_filters(tipo, categoria, origem)
    return await pool.fetchval(f"SELECT COUNT(*) FROM feed_eventos{where}", *params)

async def get_evento_por_id(pool: asyncpg.Pool, evento_id: uuid.UUID) -> dict | None:
    """Retorna um evento com payload rico.

    Para eventos antigos publicados antes do contrato rico (campo `dados`
    sem chave `versao_contrato`), compõe on-demand os blocos faltantes
    via JOIN com despesas/parlamentares/empresas/sancoes.
    """
    from app.classifiers.explicacoes import (
        criterios as criterios_do_classificador,
    )
    from app.classifiers.explicacoes import (
        gerar_titulo_narrativo,
        motivo_humano,
    )
    from app.schemas.feed import Acao, Ator, Evidencia, Objeto
    from app.services.feed_enrichment import (
        calcular_severidade,
        construir_dados_ricos,
        formatar_brl,
        formatar_cnpj,
        link_busca_cnpj,
        link_camara_deputado,
        link_portal_transparencia_sancao,
        link_recibo,
        link_senado_senador,
    )

    row = await pool.fetchrow(
        "SELECT * FROM feed_eventos WHERE id = $1",
        evento_id,
    )
    if not row:
        return None

    dados_raw = row["dados"]
    if isinstance(dados_raw, str):
        dados_raw = json.loads(dados_raw)
    dados = dados_raw or {}

    evento = {
        "id": row["id"],
        "tipo": row["tipo"],
        "categoria": row["categoria"],
        "origem": row["origem"],
        "titulo": row["titulo"],
        "descricao": row["descricao"],
        "dados": dados,
        "relevancia": float(row["relevancia"]) if row["relevancia"] else 0.5,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        "referencia_tipo": row["referencia_tipo"],
        "referencia_id": row["referencia_id"],
    }

    if isinstance(dados, dict) and dados.get("versao_contrato"):
        return evento

    if row["tipo"] == "suspeita" and row["referencia_tipo"] == "despesa" and row["referencia_id"]:
        desp = await pool.fetchrow(
            """SELECT d.id, d.ano, d.mes, d.data_emissao, d.categoria, d.subcategoria,
                   d.fornecedor, d.cnpj_cpf, d.valor_liquido, d.url_documento,
                   p.nome AS parlamentar_nome, p.partido, p.uf, p.tipo AS parlamentar_tipo,
                   p.foto_url, p.id_externo AS parlamentar_id_externo,
                   e.razao_social, e.situacao_cadastral, e.atividade_principal_descricao,
                   e.municipio AS empresa_municipio, e.uf AS empresa_uf
            FROM despesas d
            JOIN parlamentares p ON d.parlamentar_id = p.id
            LEFT JOIN empresas e ON regexp_replace(d.cnpj_cpf, '\\D', '', 'g') = e.cnpj
            WHERE d.id = $1""",
            row["referencia_id"],
        )
        if not desp:
            return evento

        cnpj_digits = "".join(ch for ch in (desp["cnpj_cpf"] or "") if ch.isdigit())
        sancoes_rows = []
        if len(cnpj_digits) == 14:
            sancoes_rows = await pool.fetch(
                """SELECT tipo, orgao_sancionador, data_inicio, data_fim
                FROM sancoes WHERE cpf_cnpj = $1
                ORDER BY data_inicio DESC NULLS LAST""",
                cnpj_digits,
            )
        orgao = sancoes_rows[0]["orgao_sancionador"] if sancoes_rows else None
        tipo_sancao = sancoes_rows[0]["tipo"] if sancoes_rows else None

        valor = float(desp["valor_liquido"] or 0)
        valor_fmt = formatar_brl(valor)
        classificador = dados.get("classificador") if isinstance(dados, dict) else None

        ator = Ator(
            nome=desp["parlamentar_nome"],
            papel="Deputado Federal" if desp["parlamentar_tipo"] == "deputado" else ("Senador" if desp["parlamentar_tipo"] == "senador" else None),
            partido=desp["partido"],
            uf=desp["uf"],
            foto_url=desp["foto_url"],
            id_externo=desp["parlamentar_id_externo"],
        )
        acao = Acao(
            verbo="pagou",
            descricao=f"{desp['categoria'] or ''}",
            valor=valor,
            valor_formatado=valor_fmt,
            data=str(desp["data_emissao"]) if desp["data_emissao"] else None,
        )
        objeto = Objeto(
            tipo="fornecedor",
            nome=desp["razao_social"] or desp["fornecedor"],
            identificador=cnpj_digits if len(cnpj_digits) == 14 else desp["cnpj_cpf"],
            identificador_formatado=formatar_cnpj(cnpj_digits) if len(cnpj_digits) == 14 else desp["cnpj_cpf"],
            detalhes={
                "situacao_cadastral": desp["situacao_cadastral"],
                "cnae": desp["atividade_principal_descricao"],
                "municipio": desp["empresa_municipio"],
                "uf_empresa": desp["empresa_uf"],
                "sancoes": [
                    {
                        "tipo": sr["tipo"],
                        "orgao": sr["orgao_sancionador"],
                        "inicio": str(sr["data_inicio"]) if sr["data_inicio"] else None,
                    }
                    for sr in sancoes_rows
                ],
            },
        )
        evidencia = None
        if classificador:
            evidencia = Evidencia(
                classificador=classificador,
                probabilidade=float(dados.get("probabilidade") or row["relevancia"] or 0),
                motivo_humano=motivo_humano(classificador),
                criterios=criterios_do_classificador(classificador),
            )

        links = [
            link_recibo(desp["url_documento"]),
            link_busca_cnpj(cnpj_digits) if len(cnpj_digits) == 14 else None,
        ]
        if desp["parlamentar_tipo"] == "senador":
            links.append(link_senado_senador(desp["parlamentar_id_externo"]))
        else:
            links.append(link_camara_deputado(desp["parlamentar_id_externo"]))
        if tipo_sancao:
            links.append(link_portal_transparencia_sancao(tipo_sancao))

        severidade = calcular_severidade(
            probabilidade=float(dados.get("probabilidade") or row["relevancia"] or 0),
            valor=valor,
            tipo_evento="suspeita",
        )

        payload = construir_dados_ricos(
            ator=ator,
            acao=acao,
            objeto=objeto,
            evidencia=evidencia,
            links=links,
            severidade=severidade,
        )

        if isinstance(dados, dict):
            for k, v in dados.items():
                if k not in payload and k not in {"versao_contrato"}:
                    payload.setdefault("_legado", {})[k] = v

        if classificador:
            contexto_titulo = {
                "parlamentar": desp["parlamentar_nome"],
                "partido": desp["partido"] or "",
                "uf": desp["uf"] or "",
                "valor": valor_fmt,
                "fornecedor": desp["fornecedor"] or "fornecedor não identificado",
                "categoria_despesa": desp["categoria"] or "",
                "orgao_sancionador": orgao or "órgão sancionador",
                "tipo_sancao": tipo_sancao or "",
            }
            evento["titulo"] = gerar_titulo_narrativo(classificador, contexto_titulo)

        evento["dados"] = payload

    return evento
