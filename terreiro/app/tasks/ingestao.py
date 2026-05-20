"""Celery tasks de ingestão de dados."""

import asyncio
import json
import logging
from datetime import date

import asyncpg
import httpx

from app.config import settings
from app.tasks.celery_app import celery

logger = logging.getLogger(__name__)

def _run_async(coro):
    """Helper para rodar coroutines em tasks Celery síncronas."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

async def _get_pool():
    return await asyncpg.create_pool(dsn=settings.database_url, min_size=1, max_size=3)

@celery.task(name="app.tasks.ingestao.ingestao_camara_deputados")
def ingestao_camara_deputados():
    """Busca deputados da legislatura atual e atualiza o banco."""
    async def run():
        from app.services.camara import CamaraService
        from app.queries.parlamentares import upsert_parlamentar
        from app.queries.raw_ingestao import inserir_raw

        pool = await _get_pool()
        try:
            async with httpx.AsyncClient(
                base_url=settings.camara_api_url, timeout=30.0,
                headers={"Accept": "application/json"},
            ) as client:
                camara = CamaraService(client)
                legislatura = await camara.buscar_legislatura_atual()
                deputados = await camara.listar_todos_deputados(legislatura=legislatura)

                for dep in deputados:
                    await inserir_raw(pool, fonte="camara", tipo="deputados", payload=dep)
                    await upsert_parlamentar(
                        pool,
                        id_externo=str(dep["id"]),
                        tipo="deputado",
                        nome=dep.get("nome", ""),
                        nome_civil=dep.get("nomeCivil"),
                        cpf=None,
                        partido=dep.get("siglaPartido"),
                        uf=dep.get("siglaUf"),
                        legislatura=legislatura,
                        foto_url=dep.get("urlFoto"),
                        email=dep.get("email"),
                        telefone=None,
                        situacao=dep.get("situacao"),
                    )

                logger.info(f"Ingestão Câmara: {len(deputados)} deputados atualizados")
        finally:
            await pool.close()

    _run_async(run())

@celery.task(name="app.tasks.ingestao.ingestao_camara_despesas")
def ingestao_camara_despesas():
    """Busca despesas do mês corrente de todos os deputados."""
    async def run():
        from app.services.camara import CamaraService
        from app.queries.despesas import upsert_despesa
        from app.queries.raw_ingestao import inserir_raw

        pool = await _get_pool()
        ano = date.today().year
        mes = date.today().month

        try:
            async with httpx.AsyncClient(
                base_url=settings.camara_api_url, timeout=30.0,
                headers={"Accept": "application/json"},
            ) as client:
                camara = CamaraService(client)

                parlamentares = await pool.fetch(
                    "SELECT id, id_externo FROM parlamentares WHERE tipo = 'deputado'"
                )

                total = 0
                for p in parlamentares:
                    try:
                        despesas = await camara.buscar_todas_despesas(
                            int(p["id_externo"]), ano=ano
                        )
                    except Exception as e:
                        logger.warning(f"Erro buscando despesas de {p['id_externo']}: {e}")
                        continue

                    for d in despesas:
                        await inserir_raw(pool, fonte="camara", tipo="despesas", payload=d)

                        data_emissao = None
                        if d.get("dataDocumento"):
                            try:
                                data_emissao = date.fromisoformat(d["dataDocumento"])
                            except (ValueError, TypeError):
                                pass

                        id_ext = f"camara-{p['id_externo']}-{d.get('codDocumento','')}-{d.get('numDocumento','')}-{ano}-{d.get('mes','')}"
                        cnpj = (d.get("cnpjCpfFornecedor") or "").replace(".", "").replace("/", "").replace("-", "")

                        await upsert_despesa(
                            pool,
                            id_externo=id_ext,
                            parlamentar_id=p["id"],
                            ano=d.get("ano", ano),
                            mes=d.get("mes", 0),
                            data_emissao=data_emissao,
                            categoria=d.get("tipoDespesa", "Não informado"),
                            subcategoria=d.get("tipoDespesa"),
                            fornecedor=d.get("nomeFornecedor"),
                            cnpj_cpf=cnpj or None,
                            documento=d.get("numDocumento"),
                            valor_documento=d.get("valorDocumento"),
                            valor_glosa=d.get("valorGlosa", 0),
                            valor_liquido=d.get("valorLiquido"),
                            url_documento=d.get("urlDocumento"),
                            lote=_to_int(d.get("codLote")),
                            ressarcimento=_to_int(d.get("numRessarcimento")),
                        )
                        total += 1

                logger.info(f"Ingestão despesas Câmara: {total} despesas atualizadas")
        finally:
            await pool.close()

    _run_async(run())

@celery.task(name="app.tasks.ingestao.ingestao_senado")
def ingestao_senado():
    """Busca senadores e despesas do ano corrente."""
    async def run():
        from app.services.senado import SenadoService
        from app.queries.parlamentares import upsert_parlamentar
        from app.queries.despesas import upsert_despesa
        from app.queries.raw_ingestao import inserir_raw

        pool = await _get_pool()
        ano = date.today().year

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                senado = SenadoService(client)

                senadores = await senado.listar_senadores()
                nome_para_id = {}
                for sen in senadores:
                    await inserir_raw(pool, fonte="senado", tipo="senadores", payload=sen)
                    record = await upsert_parlamentar(
                        pool,
                        id_externo=f"senado-{sen['codigo']}",
                        tipo="senador",
                        nome=sen.get("nome"),
                        nome_civil=sen.get("nome_completo"),
                        cpf=None,
                        partido=sen.get("partido"),
                        uf=sen.get("uf"),
                        legislatura=None,
                        foto_url=sen.get("foto_url"),
                        email=sen.get("email"),
                        telefone=None,
                        situacao="Exercício",
                    )
                    nome_para_id[sen["nome"].upper()] = record["id"]

                despesas = await senado.buscar_despesas_csv(ano)
                total = 0
                for d in despesas:
                    nome_upper = (d.get("senador") or "").upper()
                    parlamentar_id = nome_para_id.get(nome_upper)
                    if not parlamentar_id:
                        continue

                    await inserir_raw(pool, fonte="senado", tipo="despesas", payload=d)

                    data_emissao = None
                    if d.get("data"):
                        try:
                            parts = d["data"].split("/")
                            if len(parts) == 3:
                                data_emissao = date(int(parts[2]), int(parts[1]), int(parts[0]))
                        except (ValueError, IndexError):
                            pass

                    cnpj = (d.get("cnpj_cpf") or "").replace(".", "").replace("/", "").replace("-", "").strip() or None
                    id_ext = f"senado-{nome_upper}-{d.get('documento','')}-{ano}-{d.get('mes','')}"

                    await upsert_despesa(
                        pool,
                        id_externo=id_ext,
                        parlamentar_id=parlamentar_id,
                        ano=d.get("ano") or ano,
                        mes=d.get("mes") or 0,
                        data_emissao=data_emissao,
                        categoria=d.get("tipo_despesa") or "Não informado",
                        subcategoria=None,
                        fornecedor=d.get("fornecedor"),
                        cnpj_cpf=cnpj,
                        documento=d.get("documento"),
                        valor_documento=d.get("valor_reembolsado"),
                        valor_glosa=0,
                        valor_liquido=d.get("valor_reembolsado"),
                        url_documento=None,
                        lote=None,
                        ressarcimento=None,
                    )
                    total += 1

                logger.info(f"Ingestão Senado: {len(senadores)} senadores, {total} despesas")
        finally:
            await pool.close()

    _run_async(run())

@celery.task(name="app.tasks.ingestao.analise_suspeitas")
def analise_suspeitas():
    """Roda classificadores sobre despesas novas."""
    async def run():
        from app.classifiers.cnpj_cpf_invalido import CNPJCPFInvalido
        from app.classifiers.limite_subcota import LimiteSubcotaMensal

        pool = await _get_pool()
        try:
            total = 0
            for clf in [CNPJCPFInvalido(), LimiteSubcotaMensal()]:
                suspeitas = await clf.classificar(pool)
                for s in suspeitas:
                    await pool.execute(
                        """
                        INSERT INTO suspeitas (despesa_id, classificador, probabilidade, detalhes)
                        VALUES ($1, $2, $3, $4::jsonb)
                        ON CONFLICT DO NOTHING
                        """,
                        s.despesa_id, s.classificador, s.probabilidade,
                        json.dumps(s.detalhes, ensure_ascii=False),
                    )
                    total += 1
            logger.info(f"Análise: {total} suspeitas inseridas")
        finally:
            await pool.close()

    _run_async(run())

def _to_int(val, default=None):
    if val is None or val == "":
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default
