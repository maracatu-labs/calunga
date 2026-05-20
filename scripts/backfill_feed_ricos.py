"""Reprocessa eventos antigos do feed aplicando o contrato rico.

Lê eventos em `feed_eventos` sem `versao_contrato` no JSONB `dados` e
reescreve `titulo` + `dados` + `updated_at` com o payload padronizado
que os publishers novos geram. Usa batch JOINs para não cair em N+1.

Uso:
    docker compose exec api python /scripts/backfill_feed_ricos.py
"""

import argparse
import asyncio
import json
import os
import sys

import asyncpg

sys.path.insert(0, "/app")

from app.classifiers.explicacoes import (  # noqa: E402
    criterios as criterios_do_classificador,
    gerar_titulo_narrativo,
    motivo_humano,
)
from app.schemas.feed import (  # noqa: E402
    Acao,
    Ator,
    Contexto,
    Evidencia,
    LinkFeed,
    Objeto,
    Severidade,
)
from app.services.feed_enrichment import (  # noqa: E402
    calcular_severidade,
    construir_dados_ricos,
    formatar_brl,
    formatar_cnpj,
    link_camara_deputado,
    link_camara_proposicao,
    link_portal_transparencia_sancao,
    link_busca_cnpj,
    link_recibo,
    link_senado_materia,
    link_senado_senador,
    link_siop_emendas,
)

BATCH_SIZE = 500

def _extrair_classificador(dados_antigos: dict) -> str:
    """Tenta extrair classificador tanto do payload antigo (chave raiz)
    quanto do payload rico já processado (evidencia.classificador)."""
    if not isinstance(dados_antigos, dict):
        return "empresa_irregular"
    if dados_antigos.get("classificador"):
        return dados_antigos["classificador"]
    ev = dados_antigos.get("evidencia")
    if isinstance(ev, dict) and ev.get("classificador"):
        return ev["classificador"]
    legado = dados_antigos.get("_legado")
    if isinstance(legado, dict) and legado.get("classificador"):
        return legado["classificador"]
    return "empresa_irregular"

def _extrair_probabilidade(dados_antigos: dict, fallback: float = 0.5) -> float:
    if not isinstance(dados_antigos, dict):
        return fallback
    if "probabilidade" in dados_antigos:
        try:
            return float(dados_antigos["probabilidade"])
        except (TypeError, ValueError):
            pass
    ev = dados_antigos.get("evidencia")
    if isinstance(ev, dict) and ev.get("probabilidade") is not None:
        try:
            return float(ev["probabilidade"])
        except (TypeError, ValueError):
            pass
    return fallback

async def processar_suspeitas(pool: asyncpg.Pool, *, force: bool = False) -> int:
    total = 0
    cursor_id: int | None = None
    filtro_contrato = "" if force else "AND NOT (f.dados ? 'versao_contrato')"
    while True:
        params: list = [BATCH_SIZE]
        filtro_cursor = ""
        if cursor_id is not None:
            params.append(cursor_id)
            filtro_cursor = f"AND f.id < ${len(params)}"
        rows = await pool.fetch(
            f"""SELECT f.id AS feed_id, f.referencia_id,
                   d.id AS despesa_id, d.ano, d.mes, d.data_emissao,
                   d.categoria, d.subcategoria, d.fornecedor, d.cnpj_cpf,
                   d.valor_liquido, d.url_documento,
                   p.nome AS parlamentar_nome, p.partido, p.uf, p.tipo AS parlamentar_tipo,
                   p.foto_url, p.id_externo AS parlamentar_id_externo,
                   e.razao_social, e.situacao_cadastral, e.atividade_principal_descricao,
                   e.municipio AS empresa_municipio, e.uf AS empresa_uf,
                   f.dados AS dados_antigos
            FROM feed_eventos f
            JOIN despesas d ON f.referencia_id = d.id
            JOIN parlamentares p ON d.parlamentar_id = p.id
            LEFT JOIN empresas e ON regexp_replace(d.cnpj_cpf, '\\D', '', 'g') = e.cnpj
            WHERE f.tipo = 'suspeita'
              AND f.referencia_tipo = 'despesa'
              {filtro_contrato}
              {filtro_cursor}
            ORDER BY f.id DESC
            LIMIT $1""",
            *params,
        )
        if not rows:
            break
        cursor_id = rows[-1]["feed_id"]

        cnpjs = {
            "".join(ch for ch in (r["cnpj_cpf"] or "") if ch.isdigit())
            for r in rows
        }
        cnpjs = {c for c in cnpjs if len(c) == 14}
        sancao_por_cnpj: dict[str, list] = {}
        if cnpjs:
            sancoes_rows = await pool.fetch(
                """SELECT cpf_cnpj, tipo, orgao_sancionador, data_inicio, data_fim
                FROM sancoes
                WHERE cpf_cnpj = ANY($1::text[])
                ORDER BY data_inicio DESC NULLS LAST""",
                list(cnpjs),
            )
            for sr in sancoes_rows:
                sancao_por_cnpj.setdefault(sr["cpf_cnpj"], []).append(sr)

        updates: list[tuple[str, str, int]] = []
        for r in rows:
            cnpj_digits = "".join(ch for ch in (r["cnpj_cpf"] or "") if ch.isdigit())
            cnpj_valid = len(cnpj_digits) == 14
            sancoes_empresa = sancao_por_cnpj.get(cnpj_digits, [])
            orgao = sancoes_empresa[0]["orgao_sancionador"] if sancoes_empresa else None
            tipo_sancao = sancoes_empresa[0]["tipo"] if sancoes_empresa else None

            valor = float(r["valor_liquido"] or 0)
            valor_fmt = formatar_brl(valor)

            dados_antigos = r["dados_antigos"]
            if isinstance(dados_antigos, str):
                dados_antigos = json.loads(dados_antigos)
            dados_antigos = dados_antigos or {}
            classificador = _extrair_classificador(dados_antigos)
            probabilidade = _extrair_probabilidade(dados_antigos)

            contexto_titulo = {
                "parlamentar": r["parlamentar_nome"],
                "partido": r["partido"] or "",
                "uf": r["uf"] or "",
                "valor": valor_fmt,
                "fornecedor": r["fornecedor"] or "fornecedor não identificado",
                "categoria_despesa": r["categoria"] or "",
                "orgao_sancionador": orgao or "órgão sancionador",
                "tipo_sancao": tipo_sancao or "",
            }
            titulo = gerar_titulo_narrativo(classificador, contexto_titulo)

            ator = Ator(
                nome=r["parlamentar_nome"],
                papel=(
                    "Deputado Federal"
                    if r["parlamentar_tipo"] == "deputado"
                    else ("Senador" if r["parlamentar_tipo"] == "senador" else None)
                ),
                partido=r["partido"],
                uf=r["uf"],
                foto_url=r["foto_url"],
                id_externo=r["parlamentar_id_externo"],
            )
            acao = Acao(
                verbo="pagou",
                descricao=f"{r['categoria'] or ''} — {r['subcategoria'] or ''}".strip(" —"),
                valor=valor,
                valor_formatado=valor_fmt,
                data=str(r["data_emissao"]) if r["data_emissao"] else None,
            )
            objeto_detalhes = {
                "situacao_cadastral": r["situacao_cadastral"],
                "cnae": r["atividade_principal_descricao"],
                "municipio": r["empresa_municipio"],
                "uf_empresa": r["empresa_uf"],
            }
            if sancoes_empresa:
                objeto_detalhes["sancoes"] = [
                    {
                        "tipo": sr["tipo"],
                        "orgao": sr["orgao_sancionador"],
                        "inicio": str(sr["data_inicio"]) if sr["data_inicio"] else None,
                        "fim": str(sr["data_fim"]) if sr["data_fim"] else None,
                    }
                    for sr in sancoes_empresa
                ]
            objeto = Objeto(
                tipo="fornecedor",
                nome=r["razao_social"] or r["fornecedor"],
                identificador=cnpj_digits if cnpj_valid else r["cnpj_cpf"],
                identificador_formatado=formatar_cnpj(cnpj_digits) if cnpj_valid else r["cnpj_cpf"],
                detalhes={k: v for k, v in objeto_detalhes.items() if v is not None},
            )
            evidencia = Evidencia(
                classificador=classificador,
                probabilidade=probabilidade,
                motivo_humano=motivo_humano(classificador),
                criterios=criterios_do_classificador(classificador),
            )
            alertas: list[str] = []
            if sancoes_empresa:
                alertas.append(f"Empresa com {len(sancoes_empresa)} sanção(ões) registrada(s).")
            if r["situacao_cadastral"] and r["situacao_cadastral"].upper() not in ("ATIVA", "ATIVO"):
                alertas.append(f"Situação cadastral: {r['situacao_cadastral']}.")
            contexto = Contexto(alertas=alertas) if alertas else None

            links = [
                link_recibo(r["url_documento"]),
                link_busca_cnpj(cnpj_digits) if cnpj_valid else None,
            ]
            if r["parlamentar_tipo"] == "senador":
                links.append(link_senado_senador(r["parlamentar_id_externo"]))
            else:
                links.append(link_camara_deputado(r["parlamentar_id_externo"]))
            if tipo_sancao:
                links.append(link_portal_transparencia_sancao(tipo_sancao))

            severidade = calcular_severidade(
                probabilidade=probabilidade,
                valor=valor,
                tipo_evento="suspeita",
            )

            dados_ricos = construir_dados_ricos(
                ator=ator,
                acao=acao,
                objeto=objeto,
                evidencia=evidencia,
                contexto=contexto,
                links=links,
                severidade=severidade,
            )

            updates.append((titulo, json.dumps(dados_ricos, ensure_ascii=False, default=str), r["feed_id"]))

        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.executemany(
                    "UPDATE feed_eventos SET titulo = $1, dados = $2::jsonb, updated_at = NOW() WHERE id = $3",
                    updates,
                )

        total += len(updates)
        print(f"  suspeitas: {total} processadas", flush=True)

        if len(rows) < BATCH_SIZE:
            break

    return total

async def processar_votacoes(pool: asyncpg.Pool, *, force: bool = False) -> int:
    filtro_contrato = "" if force else "AND NOT (f.dados ? 'versao_contrato')"
    rows = await pool.fetch(
        f"""SELECT f.id AS feed_id, v.id AS votacao_id, v.descricao, v.sigla_tipo, v.numero, v.ano, v.casa,
               v.aprovada, v.votos_sim, v.votos_nao, v.votos_abstencao, v.data_hora, v.orgao,
               p.ementa AS proposicao_ementa, p.autor AS proposicao_autor, p.tema AS proposicao_tema,
               p.id_externo AS proposicao_id_externo, p.url_inteiro_teor
        FROM feed_eventos f
        JOIN votacoes v ON f.referencia_id = v.id
        LEFT JOIN proposicoes p ON v.proposicao_id = p.id
        WHERE f.tipo = 'votacao'
          AND f.referencia_tipo = 'votacao'
          {filtro_contrato}"""
    )
    updates = []
    for v in rows:
        aprovada = bool(v["aprovada"])
        resultado = "aprovada" if aprovada else "rejeitada"
        prop = f"{v['sigla_tipo']} {v['numero']}/{v['ano']}" if v["sigla_tipo"] else "Proposição"
        casa_nome = "Câmara" if v["casa"] == "camara" else "Senado"
        titulo = f"{prop} {resultado} no {casa_nome}"

        ementa = (v["proposicao_ementa"] or v["descricao"] or "").strip()
        descricao_partes = []
        if ementa:
            descricao_partes.append(ementa[:400])
        placar_parts = []
        if v["votos_sim"] is not None:
            placar_parts.append(f"{v['votos_sim']} sim")
        if v["votos_nao"] is not None:
            placar_parts.append(f"{v['votos_nao']} não")
        if v["votos_abstencao"]:
            placar_parts.append(f"{v['votos_abstencao']} abstenções")
        if placar_parts:
            descricao_partes.append(f"Placar: {', '.join(placar_parts)}.")
        descricao = " ".join(descricao_partes) or "Votação registrada sem ementa publicada."

        ator = Ator(nome=casa_nome, papel="Plenário" if not v["orgao"] else v["orgao"])
        acao = Acao(
            verbo="aprovou" if aprovada else "rejeitou",
            descricao=ementa[:300] if ementa else prop,
            data=v["data_hora"].isoformat() if v["data_hora"] else None,
            local=casa_nome,
        )
        objeto = Objeto(
            tipo="proposicao",
            nome=prop,
            identificador=v["proposicao_id_externo"],
            detalhes={
                "autor": v["proposicao_autor"],
                "tema": v["proposicao_tema"],
                "tipo": v["sigla_tipo"],
                "aprovada": aprovada,
                "votos_sim": v["votos_sim"],
                "votos_nao": v["votos_nao"],
                "votos_abstencao": v["votos_abstencao"],
            },
        )
        alertas = []
        if v["sigla_tipo"] == "PEC":
            alertas.append("Proposta de Emenda Constitucional: altera a Constituição Federal.")
        if v["sigla_tipo"] == "MPV":
            alertas.append("Medida Provisória: tem força de lei desde sua edição pelo Executivo.")
        contexto = Contexto(alertas=alertas) if alertas else None

        links: list[LinkFeed | None] = []
        if v["casa"] == "camara":
            links.append(link_camara_proposicao(v["sigla_tipo"], v["numero"], v["ano"]))
        else:
            links.append(link_senado_materia(v["proposicao_id_externo"]))
        if v["url_inteiro_teor"]:
            links.append(LinkFeed(
                label="Inteiro teor da proposição",
                url=v["url_inteiro_teor"],
                tipo="documento",
            ))

        severidade = Severidade.ATENCAO if v["sigla_tipo"] in ("PEC", "MPV") else Severidade.INFORMATIVO

        dados_ricos = construir_dados_ricos(
            ator=ator, acao=acao, objeto=objeto, contexto=contexto, links=links, severidade=severidade,
        )
        updates.append((titulo, descricao[:500], json.dumps(dados_ricos, ensure_ascii=False, default=str), v["feed_id"]))

    if updates:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.executemany(
                    "UPDATE feed_eventos SET titulo = $1, descricao = $2, dados = $3::jsonb, updated_at = NOW() WHERE id = $4",
                    updates,
                )
    return len(updates)

async def processar_emendas(pool: asyncpg.Pool, *, force: bool = False) -> int:
    filtro_contrato = "" if force else "AND NOT (f.dados ? 'versao_contrato')"
    rows = await pool.fetch(
        f"""SELECT f.id AS feed_id, e.id AS emenda_id, e.autor, e.tipo_emenda, e.localidade_gasto,
               e.funcao, e.subfuncao, e.valor_empenhado, e.valor_pago, e.valor_liquidado, e.ano, e.numero
        FROM feed_eventos f
        JOIN emendas e ON f.referencia_id = e.id
        WHERE f.tipo = 'emenda_pix'
          AND f.referencia_tipo = 'emenda'
          {filtro_contrato}"""
    )
    updates = []
    for e in rows:
        valor = float(e["valor_empenhado"] or 0)
        valor_fmt = formatar_brl(valor)
        autor = e["autor"] or "autor desconhecido"
        localidade = e["localidade_gasto"] or "destino não informado"

        titulo = f"{autor} destinou {valor_fmt} em emenda Pix para {localidade}"
        descricao = (
            f"Transferência especial (emenda Pix) no valor empenhado de {valor_fmt}"
            f" direcionada a {localidade} na área de {e['funcao'] or 'não classificada'}."
            " Transferências especiais vão direto ao município sem vinculação a projeto específico."
        )

        ator = Ator(nome=autor, papel="Parlamentar autor")
        acao = Acao(
            verbo="destinou",
            descricao=f"Emenda Pix {e['numero'] or ''}".strip(),
            valor=valor,
            valor_formatado=valor_fmt,
            local=localidade,
        )
        objeto = Objeto(
            tipo="emenda",
            nome=f"Emenda Pix {e['numero']}" if e["numero"] else "Emenda Pix",
            identificador=e["numero"],
            detalhes={
                "funcao": e["funcao"],
                "subfuncao": e["subfuncao"],
                "valor_empenhado": valor,
                "valor_liquidado": float(e["valor_liquidado"] or 0),
                "valor_pago": float(e["valor_pago"] or 0),
                "ano": e["ano"],
            },
        )
        contexto = Contexto(alertas=[
            "Transferência especial: recurso chega ao município sem necessidade de convênio ou plano de trabalho detalhado.",
        ])

        dados_ricos = construir_dados_ricos(
            ator=ator, acao=acao, objeto=objeto, contexto=contexto,
            links=[link_siop_emendas()],
            severidade=Severidade.ATENCAO if valor >= 1_000_000 else Severidade.INFORMATIVO,
        )
        updates.append((titulo, descricao, json.dumps(dados_ricos, ensure_ascii=False, default=str), e["feed_id"]))

    if updates:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.executemany(
                    "UPDATE feed_eventos SET titulo = $1, descricao = $2, dados = $3::jsonb, updated_at = NOW() WHERE id = $4",
                    updates,
                )
    return len(updates)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocessa também eventos que já têm versao_contrato no payload.",
    )
    args = parser.parse_args()

    dsn = os.environ.get("DATABASE_URL", "postgresql://maracatu:changeme@db:5432/maracatu")
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=4)
    try:
        modo = "FORCE (tudo)" if args.force else "só payloads antigos"
        print(f"Backfill em modo {modo}", flush=True)
        print("Processando suspeitas...", flush=True)
        n_susp = await processar_suspeitas(pool, force=args.force)
        print("Processando votações...", flush=True)
        n_vot = await processar_votacoes(pool, force=args.force)
        print("Processando emendas Pix...", flush=True)
        n_eme = await processar_emendas(pool, force=args.force)
        print(f"\nBackfill concluído: {n_susp} suspeitas, {n_vot} votações, {n_eme} emendas.")
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
