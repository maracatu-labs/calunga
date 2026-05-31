"""
Dagster definitions: Software-Defined Assets para o pipeline Maracatu.

Assets organizam o pipeline de ingestão com linhagem, partições e monitoramento.
"""

import asyncio
import json
import logging
from datetime import date

from dagster import (
    AssetExecutionContext,
    Backoff,
    DagsterRunStatus,
    DefaultSensorStatus,
    Definitions,
    RetryPolicy,
    RunRequest,
    ScheduleDefinition,
    asset,
    define_asset_job,
    run_status_sensor,
)

logger = logging.getLogger(__name__)

ANOS_BACKFILL = [2024, 2025]

JANELA_FEDERAIS_ANOS = 5

def _anos_federais_janela() -> list[int]:
    """Retorna a janela movel de anos federais (mais antigo primeiro)."""
    ano_atual = date.today().year
    return list(range(ano_atual - JANELA_FEDERAIS_ANOS + 1, ano_atual + 1))

_API_RETRY_POLICY = RetryPolicy(max_retries=3, delay=30, backoff=Backoff.EXPONENTIAL)

def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

async def _create_pool(min_size=1, max_size=5):
    import asyncpg

    from app.config import settings
    return await asyncpg.create_pool(dsn=settings.database_url, min_size=min_size, max_size=max_size)

@asset(retry_policy=_API_RETRY_POLICY, group_name="camara", description="Deputados federais da legislatura atual")
def parlamentares_camara(context: AssetExecutionContext):
    async def run():
        import httpx

        from app.config import settings
        from app.queries.parlamentares import upsert_parlamentar
        from app.queries.raw_ingestao import inserir_raw
        from app.services.camara import CamaraService

        pool = await _create_pool()
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
                        pool, id_externo=str(dep["id"]), tipo="deputado",
                        nome=dep.get("nome", ""), nome_civil=dep.get("nomeCivil"),
                        cpf=None, partido=dep.get("siglaPartido"), uf=dep.get("siglaUf"),
                        legislatura=legislatura, foto_url=dep.get("urlFoto"),
                        email=dep.get("email"), telefone=None, situacao=dep.get("situacao"),
                    )
                context.log.info(f"Atualizados {len(deputados)} deputados")
        finally:
            await pool.close()

    _run_async(run())

@asset(retry_policy=_API_RETRY_POLICY, group_name="camara", deps=[parlamentares_camara], description="Despesas CEAP da Câmara")
def despesas_camara(context: AssetExecutionContext):
    async def run():
        import httpx

        from app.config import settings
        from app.queries.despesas import upsert_despesa
        from app.queries.parlamentares import upsert_parlamentar
        from app.queries.raw_ingestao import inserir_raw
        from app.services.camara import CamaraService

        def _to_int(val, default=None):
            if val is None or val == "":
                return default
            try:
                return int(val)
            except (ValueError, TypeError):
                return default

        def _to_float(val, default=None):
            if val is None or val == "":
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        def _clean_cnpj(val):
            if not val:
                return None
            return str(val).replace(".", "").replace("/", "").replace("-", "").strip() or None

        pool = await _create_pool()
        try:
            async with httpx.AsyncClient(
                base_url=settings.camara_api_url, timeout=30.0,
                headers={"Accept": "application/json"},
            ) as client:
                camara = CamaraService(client)
                legislatura = await camara.buscar_legislatura_atual()
                deputados_api = await camara.listar_todos_deputados(legislatura=legislatura)

                deputados = []
                for dep in deputados_api:
                    await inserir_raw(pool, fonte="camara", tipo="deputados", payload=dep)
                    record = await upsert_parlamentar(
                        pool, id_externo=str(dep["id"]), tipo="deputado",
                        nome=dep.get("nome", ""), nome_civil=dep.get("nomeCivil"),
                        cpf=None, partido=dep.get("siglaPartido"), uf=dep.get("siglaUf"),
                        legislatura=legislatura, foto_url=dep.get("urlFoto"),
                        email=dep.get("email"), telefone=None, situacao=dep.get("situacao"),
                    )
                    deputados.append({"id": record["id"], "id_externo": dep["id"], "nome": dep["nome"]})

                total = 0
                for i, dep in enumerate(deputados, 1):
                    context.log.info(f"[{i}/{len(deputados)}] Despesas de {dep['nome']}")
                    for ano in [date.today().year - 1, date.today().year]:
                        try:
                            despesas = await camara.buscar_todas_despesas(dep["id_externo"], ano=ano)
                        except Exception as e:
                            context.log.warning(f"Erro {dep['nome']} {ano}: {e}")
                            continue

                        for d in despesas:
                            await inserir_raw(pool, fonte="camara", tipo="despesas", payload=d)

                            id_externo = f"camara-{dep['id_externo']}-{d.get('codDocumento', '')}-{d.get('numDocumento', '')}-{ano}-{d.get('mes', '')}"
                            data_emissao = None
                            if d.get("dataDocumento"):
                                try:
                                    data_emissao = date.fromisoformat(d["dataDocumento"])
                                except (ValueError, TypeError):
                                    pass

                            await upsert_despesa(
                                pool, id_externo=id_externo, parlamentar_id=dep["id"],
                                ano=_to_int(d.get("ano"), ano), mes=_to_int(d.get("mes"), 0),
                                data_emissao=data_emissao,
                                categoria=d.get("tipoDespesa", "Não informado"),
                                subcategoria=d.get("tipoDespesa"),
                                fornecedor=d.get("nomeFornecedor"),
                                cnpj_cpf=_clean_cnpj(d.get("cnpjCpfFornecedor")),
                                documento=d.get("numDocumento"),
                                valor_documento=_to_float(d.get("valorDocumento")),
                                valor_glosa=_to_float(d.get("valorGlosa"), 0),
                                valor_liquido=_to_float(d.get("valorLiquido")),
                                url_documento=d.get("urlDocumento"),
                                lote=_to_int(d.get("codLote")),
                                ressarcimento=_to_int(d.get("numRessarcimento")),
                            )
                            total += 1

                context.log.info(f"Total: {total} despesas da Câmara")
        finally:
            await pool.close()

    _run_async(run())

@asset(retry_policy=_API_RETRY_POLICY, group_name="senado", description="Senadores em exercício + despesas CEAP")
def senado(context: AssetExecutionContext):
    async def run():
        import httpx

        from app.queries.despesas import upsert_despesa
        from app.queries.parlamentares import upsert_parlamentar
        from app.queries.raw_ingestao import inserir_raw
        from app.services.senado import SenadoService

        pool = await _create_pool()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                senado_svc = SenadoService(client)

                senadores = await senado_svc.listar_senadores()
                nome_para_id = {}
                for sen in senadores:
                    await inserir_raw(pool, fonte="senado", tipo="senadores", payload=sen)
                    record = await upsert_parlamentar(
                        pool, id_externo=f"senado-{sen['codigo']}", tipo="senador",
                        nome=sen.get("nome"), nome_civil=sen.get("nome_completo"),
                        cpf=None, partido=sen.get("partido"), uf=sen.get("uf"),
                        legislatura=None, foto_url=sen.get("foto_url"),
                        email=sen.get("email"), telefone=None, situacao="Exercício",
                    )
                    nome_para_id[sen["nome"].upper()] = record["id"]

                context.log.info(f"{len(nome_para_id)} senadores atualizados")

                total = 0
                for ano in [date.today().year - 1, date.today().year]:
                    try:
                        despesas = await senado_svc.buscar_despesas_csv(ano)
                    except Exception as e:
                        context.log.warning(f"Erro despesas Senado {ano}: {e}")
                        continue

                    for d in despesas:
                        nome_upper = (d.get("senador") or "").upper()
                        parlamentar_id = nome_para_id.get(nome_upper)
                        if not parlamentar_id:
                            continue

                        await inserir_raw(pool, fonte="senado", tipo="despesas", payload=d)

                        data_emissao = None
                        if d.get("data"):
                            try:
                                data_emissao = date.fromisoformat(d["data"])
                            except (ValueError, TypeError):
                                try:
                                    parts = d["data"].split("/")
                                    if len(parts) == 3:
                                        data_emissao = date(int(parts[2]), int(parts[1]), int(parts[0]))
                                except (ValueError, IndexError):
                                    pass

                        cnpj_cpf = (d.get("cnpj_cpf") or "").replace(".", "").replace("/", "").replace("-", "").strip() or None
                        id_externo = f"senado-{nome_upper}-{d.get('documento', '')}-{ano}-{d.get('mes', '')}"

                        await upsert_despesa(
                            pool, id_externo=id_externo, parlamentar_id=parlamentar_id,
                            ano=d.get("ano") or ano, mes=d.get("mes") or 0,
                            data_emissao=data_emissao,
                            categoria=d.get("tipo_despesa") or "Não informado",
                            subcategoria=None, fornecedor=d.get("fornecedor"),
                            cnpj_cpf=cnpj_cpf, documento=d.get("documento"),
                            valor_documento=d.get("valor_reembolsado"), valor_glosa=0,
                            valor_liquido=d.get("valor_reembolsado"),
                            url_documento=None, lote=None, ressarcimento=None,
                        )
                        total += 1

                context.log.info(f"Total: {total} despesas do Senado")
        finally:
            await pool.close()

    _run_async(run())

@asset(retry_policy=_API_RETRY_POLICY, group_name="cnpj", description="Base CNPJ da Receita Federal (bulk, só fornecedores das despesas)")
def empresas_cnpj(context: AssetExecutionContext):
    async def run():
        import csv
        import io
        import re
        import zipfile
        from pathlib import Path

        import httpx

        WEBDAV_BASE = "https://arquivos.receitafederal.gov.br/public.php/webdav"
        SHARE_TOKEN = "YggdBLfdninEJX9"
        AUTH = httpx.BasicAuth(SHARE_TOKEN, "")
        DATA_DIR = Path("/tmp/cnpj_data")
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        SITUACAO_MAP = {"01": "NULA", "02": "ATIVA", "03": "SUSPENSA", "04": "INAPTA", "08": "BAIXADA"}
        EMPRESAS_FIELDS = [
            "cnpj_basico", "razao_social", "natureza_juridica",
            "qualificacao_responsavel", "capital_social", "porte", "ente_federativo",
        ]
        ESTABELECIMENTOS_FIELDS = [
            "cnpj_basico", "cnpj_ordem", "cnpj_dv", "matriz_filial", "nome_fantasia",
            "situacao_cadastral", "data_situacao", "motivo_situacao", "cidade_exterior",
            "pais", "data_inicio", "cnae_principal", "cnae_secundaria",
            "tipo_logradouro", "logradouro", "numero", "complemento", "bairro",
            "cep", "uf", "municipio", "ddd1", "telefone1", "ddd2", "telefone2",
            "ddd_fax", "fax", "email", "situacao_especial", "data_situacao_especial",
        ]

        def iter_csv_from_zip(zip_path, fields):
            """Yield rows one by one, sem carregar o CSV inteiro em memoria."""
            with zipfile.ZipFile(zip_path) as zf:
                for name in zf.namelist():
                    with zf.open(name) as f:

                        text = io.TextIOWrapper(f, encoding="latin-1", newline="")
                        reader = csv.reader(text, delimiter=";", quotechar='"')
                        for line in reader:
                            if len(line) >= len(fields):
                                yield {fields[i]: line[i].strip().strip('"') for i in range(len(fields))}

        def parse_date(val):
            val = val.strip()
            if not val or val == "0" or len(val) != 8:
                return None
            try:
                return date(int(val[:4]), int(val[4:6]), int(val[6:8]))
            except (ValueError, IndexError):
                return None

        def parse_decimal(val):
            val = val.strip().replace(",", ".")
            if not val:
                return None
            try:
                return float(val)
            except ValueError:
                return None

        pool = await _create_pool(max_size=10)
        try:

            rows = await pool.fetch(
                """
                SELECT DISTINCT cnpj_basico FROM (
                    SELECT LEFT(cnpj_cpf, 8) AS cnpj_basico FROM despesas
                        WHERE cnpj_cpf IS NOT NULL AND LENGTH(cnpj_cpf) >= 8
                    UNION
                    SELECT LEFT(fornecedor_cnpj_cpf, 8) FROM contratos
                        WHERE fornecedor_cnpj_cpf IS NOT NULL AND LENGTH(fornecedor_cnpj_cpf) >= 8
                    UNION
                    SELECT LEFT(favorecido_cnpj_cpf, 8) FROM despesas_orcamentarias
                        WHERE favorecido_cnpj_cpf IS NOT NULL AND LENGTH(favorecido_cnpj_cpf) >= 8
                    UNION
                    SELECT LEFT(cnpj_cpf_favorecido, 8) FROM cpgf
                        WHERE cnpj_cpf_favorecido IS NOT NULL AND LENGTH(cnpj_cpf_favorecido) >= 8
                ) q WHERE cnpj_basico IS NOT NULL
                """
            )
            cnpjs_filter = {r["cnpj_basico"] for r in rows}
            context.log.info(f"Filtrando por {len(cnpjs_filter)} CNPJs relevantes")

            async with httpx.AsyncClient(timeout=300.0, auth=AUTH, follow_redirects=True) as client:
                resp = await client.request(
                    "PROPFIND", f"{WEBDAV_BASE}/", headers={"Depth": "1"},
                )
                resp.raise_for_status()
                meses = sorted(set(re.findall(r"/public\.php/webdav/(\d{4}-\d{2})/", resp.text)))
                if not meses:
                    context.log.warning("Nenhum mes encontrado no WebDAV da RF")
                    return
                mes_alvo = meses[-1]
                context.log.info(f"Mes mais recente disponivel: {mes_alvo}")

                resp = await client.request(
                    "PROPFIND", f"{WEBDAV_BASE}/{mes_alvo}/", headers={"Depth": "1"},
                )
                resp.raise_for_status()

                arquivos = sorted(set(re.findall(
                    rf"/public\.php/webdav/{mes_alvo}/((?:Empresas|Estabelecimentos)\d+\.zip)",
                    resp.text,
                )))
                context.log.info(f"Arquivos a baixar: {len(arquivos)}")

                for filename in arquivos:
                    filepath = DATA_DIR / filename
                    if filepath.exists() and filepath.stat().st_size > 0:
                        context.log.info(f"{filename} ja em cache, pulando")
                        continue
                    url = f"{WEBDAV_BASE}/{mes_alvo}/{filename}"
                    context.log.info(f"Baixando {filename}...")
                    try:
                        async with client.stream("GET", url) as resp:
                            resp.raise_for_status()
                            with open(filepath, "wb") as f:
                                async for chunk in resp.aiter_bytes(chunk_size=4 * 1024 * 1024):
                                    f.write(chunk)
                        context.log.info(f"  {filename}: {filepath.stat().st_size / 1024**2:.0f} MB")
                    except Exception as e:
                        context.log.warning(f"Erro baixando {filename}: {e}")
                        if filepath.exists():
                            filepath.unlink()

            total_emp = 0
            for zip_path in sorted(DATA_DIR.glob("Empresa*.zip")):
                context.log.info(f"Processando {zip_path.name}...")
                batch = []
                for row in iter_csv_from_zip(zip_path, EMPRESAS_FIELDS):
                    if row["cnpj_basico"] not in cnpjs_filter:
                        continue
                    batch.append((
                        row["cnpj_basico"], row.get("razao_social") or None,
                        row.get("natureza_juridica") or None, row.get("qualificacao_responsavel") or None,
                        parse_decimal(row.get("capital_social", "")),
                        row.get("porte") or None, row.get("ente_federativo") or None,
                    ))
                    if len(batch) >= 5000:
                        async with pool.acquire() as conn:
                            await conn.executemany(
                                """INSERT INTO empresas (cnpj, cnpj_basico, razao_social, natureza_juridica,
                                    qualificacao_responsavel, capital_social, porte, ente_federativo, fonte)
                                VALUES ($1, $1, $2, $3, $4, $5, $6, $7, 'bulk')
                                ON CONFLICT (cnpj) DO UPDATE SET
                                    razao_social = COALESCE(EXCLUDED.razao_social, empresas.razao_social),
                                    natureza_juridica = COALESCE(EXCLUDED.natureza_juridica, empresas.natureza_juridica),
                                    capital_social = COALESCE(EXCLUDED.capital_social, empresas.capital_social),
                                    porte = COALESCE(EXCLUDED.porte, empresas.porte),
                                    updated_at = NOW()""",
                                [(r[0], r[1], r[2], r[3], r[4], r[5], r[6]) for r in batch],
                            )
                        total_emp += len(batch)
                        batch = []
                if batch:
                    async with pool.acquire() as conn:
                        await conn.executemany(
                            """INSERT INTO empresas (cnpj, cnpj_basico, razao_social, natureza_juridica,
                                qualificacao_responsavel, capital_social, porte, ente_federativo, fonte)
                            VALUES ($1, $1, $2, $3, $4, $5, $6, $7, 'bulk')
                            ON CONFLICT (cnpj) DO UPDATE SET
                                razao_social = COALESCE(EXCLUDED.razao_social, empresas.razao_social),
                                natureza_juridica = COALESCE(EXCLUDED.natureza_juridica, empresas.natureza_juridica),
                                capital_social = COALESCE(EXCLUDED.capital_social, empresas.capital_social),
                                porte = COALESCE(EXCLUDED.porte, empresas.porte),
                                updated_at = NOW()""",
                            [(r[0], r[1], r[2], r[3], r[4], r[5], r[6]) for r in batch],
                        )
                    total_emp += len(batch)

            context.log.info(f"Total empresas: {total_emp}")

            total_est = 0
            for zip_path in sorted(DATA_DIR.glob("Estabelecimento*.zip")):
                context.log.info(f"Processando {zip_path.name}...")
                batch = []
                for row in iter_csv_from_zip(zip_path, ESTABELECIMENTOS_FIELDS):
                    if row["cnpj_basico"] not in cnpjs_filter:
                        continue
                    cnpj_full = f"{row['cnpj_basico']}{row.get('cnpj_ordem', '0001')}{row.get('cnpj_dv', '00')}"
                    sit_code = row.get("situacao_cadastral", "")
                    situacao = SITUACAO_MAP.get(sit_code.zfill(2), sit_code)
                    batch.append((
                        cnpj_full, row["cnpj_basico"], row.get("cnpj_ordem") or None,
                        row.get("cnpj_dv") or None, row.get("matriz_filial") or None,
                        row.get("nome_fantasia") or None, situacao,
                        parse_date(row.get("data_situacao", "")),
                        row.get("motivo_situacao") or None,
                        parse_date(row.get("data_inicio", "")),
                        row.get("cnae_principal") or None, row.get("cnae_secundaria") or None,
                        row.get("tipo_logradouro") or None, row.get("logradouro") or None,
                        row.get("numero") or None, row.get("complemento") or None,
                        row.get("bairro") or None, row.get("cep") or None,
                        row.get("uf") or None, row.get("municipio") or None,
                        row.get("ddd1") or None, row.get("telefone1") or None,
                        row.get("email") or None,
                    ))
                    if len(batch) >= 5000:
                        async with pool.acquire() as conn:
                            await conn.executemany(
                                """INSERT INTO empresas (cnpj, cnpj_basico, cnpj_ordem, cnpj_dv, matriz_filial,
                                    nome_fantasia, situacao_cadastral, data_situacao, motivo_situacao,
                                    data_abertura, atividade_principal_codigo, cnae_secundaria,
                                    tipo_logradouro, logradouro, numero, complemento, bairro,
                                    cep, uf, municipio, ddd, telefone, email, fonte)
                                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,'bulk')
                                ON CONFLICT (cnpj) DO UPDATE SET
                                    nome_fantasia = COALESCE(EXCLUDED.nome_fantasia, empresas.nome_fantasia),
                                    situacao_cadastral = COALESCE(EXCLUDED.situacao_cadastral, empresas.situacao_cadastral),
                                    data_situacao = COALESCE(EXCLUDED.data_situacao, empresas.data_situacao),
                                    motivo_situacao = COALESCE(EXCLUDED.motivo_situacao, empresas.motivo_situacao),
                                    data_abertura = COALESCE(EXCLUDED.data_abertura, empresas.data_abertura),
                                    atividade_principal_codigo = COALESCE(EXCLUDED.atividade_principal_codigo, empresas.atividade_principal_codigo),
                                    logradouro = COALESCE(EXCLUDED.logradouro, empresas.logradouro),
                                    uf = COALESCE(EXCLUDED.uf, empresas.uf),
                                    municipio = COALESCE(EXCLUDED.municipio, empresas.municipio),
                                    cep = COALESCE(EXCLUDED.cep, empresas.cep),
                                    email = COALESCE(EXCLUDED.email, empresas.email),
                                    updated_at = NOW()""",
                                batch,
                            )
                        total_est += len(batch)
                        batch = []
                if batch:
                    async with pool.acquire() as conn:
                        await conn.executemany(
                            """INSERT INTO empresas (cnpj, cnpj_basico, cnpj_ordem, cnpj_dv, matriz_filial,
                                nome_fantasia, situacao_cadastral, data_situacao, motivo_situacao,
                                data_abertura, atividade_principal_codigo, cnae_secundaria,
                                tipo_logradouro, logradouro, numero, complemento, bairro,
                                cep, uf, municipio, ddd, telefone, email, fonte)
                            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,'bulk')
                            ON CONFLICT (cnpj) DO UPDATE SET
                                nome_fantasia = COALESCE(EXCLUDED.nome_fantasia, empresas.nome_fantasia),
                                situacao_cadastral = COALESCE(EXCLUDED.situacao_cadastral, empresas.situacao_cadastral),
                                data_situacao = COALESCE(EXCLUDED.data_situacao, empresas.data_situacao),
                                motivo_situacao = COALESCE(EXCLUDED.motivo_situacao, empresas.motivo_situacao),
                                data_abertura = COALESCE(EXCLUDED.data_abertura, empresas.data_abertura),
                                atividade_principal_codigo = COALESCE(EXCLUDED.atividade_principal_codigo, empresas.atividade_principal_codigo),
                                logradouro = COALESCE(EXCLUDED.logradouro, empresas.logradouro),
                                uf = COALESCE(EXCLUDED.uf, empresas.uf),
                                municipio = COALESCE(EXCLUDED.municipio, empresas.municipio),
                                cep = COALESCE(EXCLUDED.cep, empresas.cep),
                                email = COALESCE(EXCLUDED.email, empresas.email),
                                updated_at = NOW()""",
                            batch,
                        )
                    total_est += len(batch)

            context.log.info(f"Total estabelecimentos: {total_est}")
        finally:
            await pool.close()

    _run_async(run())

@asset(retry_policy=_API_RETRY_POLICY, group_name="transparencia", description="Sanções CEIS/CNEP/CEPIM")
def sancoes(context: AssetExecutionContext):
    async def run():
        import httpx

        from app.config import settings
        from app.services.transparencia import TransparenciaService

        def _clean_doc(val):
            if not val:
                return None

            cleaned = "".join(c for c in str(val) if c.isdigit())
            if not cleaned or len(cleaned) > 14:
                return None
            return cleaned

        def _extract_cnpj(record):

            for key in ["pessoa", "pessoaJuridica"]:
                obj = record.get(key) or {}
                for campo in ["cnpjFormatado", "cpfFormatado", "numeroInscricaoSocial"]:
                    doc = _clean_doc(obj.get(campo))
                    if doc:
                        return doc

            sanc = record.get("sancionado") or {}
            return _clean_doc(sanc.get("codigoFormatado"))

        def _extract_nome(record):
            for key in ["pessoa", "pessoaJuridica", "sancionado"]:
                obj = record.get(key) or {}
                nome = obj.get("nome") or obj.get("razaoSocialReceita")
                if nome:
                    return nome.strip()
            return None

        def _extract_orgao(record):

            for key in ["orgaoSancionador", "orgaoSuperior"]:
                orgao = record.get(key) or {}
                if isinstance(orgao, dict):
                    nome = orgao.get("nome") or orgao.get("siglaUf")
                    if nome:
                        return nome
            return None

        def _extract_fundamentacao(record):

            fund = record.get("fundamentacao")
            if isinstance(fund, list) and fund:
                return fund[0].get("descricao") or fund[0].get("codigo")
            if isinstance(fund, str):
                return fund
            return record.get("motivo")

        def _extract_date(record, key):
            val = record.get(key, "")
            if not val or val == "Sem informação":
                return None
            try:
                if "/" in val:
                    parts = val.split("/")
                    if len(parts) == 3:
                        return date(int(parts[2]), int(parts[1]), int(parts[0]))
                if len(val) >= 10 and val[4] == "-":
                    return date(int(val[0:4]), int(val[5:7]), int(val[8:10]))
            except (ValueError, IndexError):
                return None
            return None

        pool = await _create_pool()
        try:
            async with httpx.AsyncClient(
                base_url="https://api.portaldatransparencia.gov.br/api-de-dados",
                timeout=30.0,
                headers={"chave-api-dados": settings.transparencia_api_token, "Accept": "application/json"},
            ) as client:
                service = TransparenciaService(client)

                for tipo, fetcher in [("CEIS", service.buscar_ceis), ("CNEP", service.buscar_cnep), ("CEPIM", service.buscar_cepim)]:
                    try:
                        records = await fetcher()
                        total = 0
                        for record in records:
                            cpf_cnpj = _extract_cnpj(record)
                            if not cpf_cnpj:
                                continue
                            try:
                                await pool.execute(
                                    """INSERT INTO sancoes (tipo, cpf_cnpj, nome, orgao_sancionador, fundamentacao_legal, data_inicio, data_fim)
                                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                                    ON CONFLICT DO NOTHING""",
                                    tipo, cpf_cnpj, _extract_nome(record), _extract_orgao(record),
                                    _extract_fundamentacao(record),
                                    _extract_date(record, "dataInicioSancao") or _extract_date(record, "dataPublicacaoSancao"),
                                    _extract_date(record, "dataFimSancao") or _extract_date(record, "dataFinalSancao"),
                                )
                                total += 1
                            except Exception as e:
                                context.log.warning(f"Erro sanção {cpf_cnpj}: {e}")
                        context.log.info(f"{tipo}: {total} sanções inseridas de {len(records)} registros")
                    except Exception as e:
                        context.log.warning(f"Erro ingerindo {tipo}: {e}")
        finally:
            await pool.close()

    _run_async(run())

@asset(retry_policy=_API_RETRY_POLICY, group_name="tse", description="Candidatos e prestação de contas do TSE")
def candidatos_tse(context: AssetExecutionContext):
    async def run():
        import csv
        import io
        import zipfile
        from pathlib import Path

        import httpx

        DATA_DIR = Path("/tmp/tse_data")
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        TSE_URL = "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_{ano}.zip"

        def _int(val):
            try:
                return int(str(val).strip())
            except (ValueError, TypeError):
                return None

        def _clean_doc(val):
            v = val.replace(".", "").replace("/", "").replace("-", "").strip()
            return v if v and v != "0" else None

        anos = [2022, 2024]

        pool = await _create_pool()
        try:
            for ano in anos:
                filepath = DATA_DIR / f"consulta_cand_{ano}.zip"

                if not filepath.exists():
                    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                        url = TSE_URL.format(ano=ano)
                        context.log.info(f"Baixando {url}...")
                        async with client.stream("GET", url) as resp:
                            resp.raise_for_status()
                            with open(filepath, "wb") as f:
                                async for chunk in resp.aiter_bytes(chunk_size=1024 * 1024):
                                    f.write(chunk)

                candidatos = []
                with zipfile.ZipFile(filepath) as zf:
                    for name in zf.namelist():
                        if not name.endswith(".csv"):
                            continue
                        with zf.open(name) as f:
                            try:
                                text = f.read().decode("latin-1")
                            except UnicodeDecodeError:
                                text = f.read().decode("utf-8")
                            reader = csv.DictReader(io.StringIO(text), delimiter=";", quotechar='"')
                            for row in reader:
                                candidatos.append((
                                    _int(row.get("ANO_ELEICAO") or row.get("DT_ELEICAO", "")[:4]),
                                    (row.get("DS_ELEICAO") or "").strip(),
                                    (row.get("SG_UF") or "").strip(),
                                    (row.get("DS_CARGO") or "").strip(),
                                    (row.get("NR_CANDIDATO") or "").strip(),
                                    (row.get("NM_CANDIDATO") or "").strip(),
                                    (row.get("NM_URNA_CANDIDATO") or "").strip(),
                                    _clean_doc(row.get("NR_CPF_CANDIDATO", "")),
                                    _clean_doc(row.get("NR_CNPJ_PRESTADOR_CONTA", "")),
                                    (row.get("SG_PARTIDO") or "").strip(),
                                    (row.get("DS_SIT_TOT_TURNO") or row.get("DS_SITUACAO_CANDIDATURA") or "").strip(),
                                ))

                context.log.info(f"Parseados {len(candidatos)} candidatos de {ano}")

                total = 0
                for i in range(0, len(candidatos), 5000):
                    batch = candidatos[i:i + 5000]
                    async with pool.acquire() as conn:
                        await conn.executemany(
                            """INSERT INTO candidatos_tse (ano_eleicao, tipo_eleicao, uf, cargo, numero_candidato,
                                nome, nome_urna, cpf, cnpj_campanha, partido, situacao)
                            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)""",
                            batch,
                        )
                    total += len(batch)
                context.log.info(f"Inseridos {total} candidatos de {ano}")
        finally:
            await pool.close()

    _run_async(run())

@asset(
    group_name="analise",
    deps=[despesas_camara, senado, empresas_cnpj, sancoes],
    description="Classificadores de anomalias (Gonguê)",
)
def suspeitas(context: AssetExecutionContext):
    async def run():
        from app.classifiers.cnpj_cpf_invalido import CNPJCPFInvalido
        from app.classifiers.despesa_eleitoral import DespesaEleitoral
        from app.classifiers.despesa_fim_de_semana import DespesaFimDeSemana
        from app.classifiers.empresa_irregular import EmpresaIrregular
        from app.classifiers.explicacoes import (
            criterios as criterios_do_classificador,
        )
        from app.classifiers.explicacoes import (
            gerar_titulo_narrativo,
            motivo_humano,
        )
        from app.classifiers.limite_subcota import LimiteSubcotaMensal
        from app.classifiers.preco_refeicao import PrecoRefeicaoAnomalo
        from app.queries.feed import publicar_evento
        from app.schemas.feed import Acao, Ator, Contexto, Evidencia, Objeto
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

        classifiers = [
            CNPJCPFInvalido(), LimiteSubcotaMensal(), EmpresaIrregular(),
            DespesaEleitoral(), DespesaFimDeSemana(), PrecoRefeicaoAnomalo(),
        ]

        pool = await _create_pool()
        try:
            total = 0
            total_feed = 0
            for clf in classifiers:
                context.log.info(f"Rodando classificador: {clf.name}")
                found = await clf.classificar(pool)
                if not found:
                    continue

                relevantes = [s for s in found if s.probabilidade >= 0.5]
                despesa_ids = list({s.despesa_id for s in relevantes})
                despesa_map: dict = {}
                sancao_por_cnpj: dict = {}
                if despesa_ids:
                    rows = await pool.fetch(
                        """SELECT d.id, d.parlamentar_id, d.ano, d.mes, d.data_emissao,
                               d.categoria, d.subcategoria, d.fornecedor, d.cnpj_cpf,
                               d.valor_liquido, d.url_documento,
                               p.nome AS parlamentar_nome, p.partido, p.uf, p.tipo AS parlamentar_tipo,
                               p.foto_url, p.id_externo AS parlamentar_id_externo,
                               e.razao_social, e.nome_fantasia, e.situacao_cadastral,
                               e.atividade_principal_descricao, e.municipio AS empresa_municipio,
                               e.uf AS empresa_uf
                        FROM despesas d
                        JOIN parlamentares p ON d.parlamentar_id = p.id
                        LEFT JOIN empresas e ON regexp_replace(d.cnpj_cpf, '\\D', '', 'g') = e.cnpj
                        WHERE d.id = ANY($1::uuid[])""",
                        despesa_ids,
                    )
                    despesa_map = {row["id"]: row for row in rows}

                    cnpjs = {
                        "".join(ch for ch in (row["cnpj_cpf"] or "") if ch.isdigit())
                        for row in rows
                    }
                    cnpjs = {c for c in cnpjs if len(c) == 14}
                    if cnpjs:
                        sancoes_rows = await pool.fetch(
                            """SELECT cpf_cnpj, tipo, orgao_sancionador, data_inicio, data_fim,
                                   fundamentacao_legal
                            FROM sancoes
                            WHERE cpf_cnpj = ANY($1::text[])
                            ORDER BY data_inicio DESC NULLS LAST""",
                            list(cnpjs),
                        )
                        for sr in sancoes_rows:
                            sancao_por_cnpj.setdefault(sr["cpf_cnpj"], []).append(sr)

                for s in found:
                    result = await pool.fetchrow(
                        """INSERT INTO suspeitas (despesa_id, classificador, probabilidade, detalhes)
                        VALUES ($1, $2, $3, $4::jsonb)
                        ON CONFLICT DO NOTHING RETURNING id""",
                        s.despesa_id, s.classificador, s.probabilidade,
                        json.dumps(s.detalhes, ensure_ascii=False),
                    )
                    total += 1

                    if not (result and s.probabilidade >= 0.5):
                        continue
                    desp = despesa_map.get(s.despesa_id)
                    if not desp:
                        continue

                    cnpj_digits = "".join(ch for ch in (desp["cnpj_cpf"] or "") if ch.isdigit())
                    cnpj_valid = len(cnpj_digits) == 14
                    valor = float(desp["valor_liquido"] or 0)
                    valor_fmt = formatar_brl(valor)
                    sancoes_empresa = sancao_por_cnpj.get(cnpj_digits, [])
                    orgao = sancoes_empresa[0]["orgao_sancionador"] if sancoes_empresa else None
                    tipo_sancao = sancoes_empresa[0]["tipo"] if sancoes_empresa else None

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
                    titulo = gerar_titulo_narrativo(s.classificador, contexto_titulo)

                    descricao = (
                        f"{desp['parlamentar_nome']} ({desp['partido']}/{desp['uf']})"
                        f" gastou {valor_fmt} com {desp['fornecedor'] or 'fornecedor não identificado'}"
                        f" na categoria {desp['categoria'] or 'não informada'}."
                    )
                    motivo_suspeita = s.detalhes.get("motivo") if isinstance(s.detalhes, dict) else None
                    if motivo_suspeita:
                        descricao += f" {motivo_suspeita}"

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
                        descricao=f"{desp['categoria'] or ''} — {desp['subcategoria'] or ''}".strip(" —"),
                        valor=valor,
                        valor_formatado=valor_fmt,
                        data=str(desp["data_emissao"]) if desp["data_emissao"] else None,
                    )
                    objeto_detalhes = {
                        "situacao_cadastral": desp["situacao_cadastral"],
                        "cnae": desp["atividade_principal_descricao"],
                        "municipio": desp["empresa_municipio"],
                        "uf_empresa": desp["empresa_uf"],
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
                        nome=desp["razao_social"] or desp["fornecedor"],
                        identificador=cnpj_digits if cnpj_valid else desp["cnpj_cpf"],
                        identificador_formatado=formatar_cnpj(cnpj_digits) if cnpj_valid else desp["cnpj_cpf"],
                        detalhes={k: v for k, v in objeto_detalhes.items() if v is not None},
                    )
                    evidencia = Evidencia(
                        classificador=s.classificador,
                        probabilidade=float(s.probabilidade),
                        motivo_humano=motivo_humano(s.classificador),
                        criterios=criterios_do_classificador(s.classificador),
                    )
                    alertas: list[str] = []
                    if sancoes_empresa:
                        alertas.append(f"Empresa com {len(sancoes_empresa)} sanção(ões) registrada(s).")
                    if desp["situacao_cadastral"] and desp["situacao_cadastral"].upper() not in ("ATIVA", "ATIVO"):
                        alertas.append(f"Situação cadastral: {desp['situacao_cadastral']}.")
                    contexto = Contexto(alertas=alertas) if alertas else None

                    links = [
                        link_recibo(desp["url_documento"]),
                        link_busca_cnpj(cnpj_digits) if cnpj_valid else None,
                    ]
                    if desp["parlamentar_tipo"] == "senador":
                        links.append(link_senado_senador(desp["parlamentar_id_externo"]))
                    else:
                        links.append(link_camara_deputado(desp["parlamentar_id_externo"]))
                    if tipo_sancao:
                        links.append(link_portal_transparencia_sancao(tipo_sancao))

                    severidade = calcular_severidade(
                        probabilidade=float(s.probabilidade),
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

                    await publicar_evento(
                        pool,
                        tipo="suspeita",
                        categoria="irregularidade",
                        origem="dagster",
                        titulo=titulo,
                        descricao=descricao,
                        dados=dados_ricos,
                        referencia_tipo="despesa",
                        referencia_id=s.despesa_id,
                        relevancia=float(s.probabilidade),
                    )
                    total_feed += 1

            context.log.info(f"Total: {total} suspeitas, {total_feed} eventos no feed")
        finally:
            await pool.close()

    _run_async(run())

@asset(group_name="analise", deps=[despesas_camara], description="Análise de recibos via OCR + LLM")
def analise_recibos(context: AssetExecutionContext):
    async def run():
        from app.services.ocr import process_receipt

        pool = await _create_pool(max_size=3)
        try:
            rows = await pool.fetch(
                """SELECT d.id, d.url_documento, d.fornecedor, d.valor_liquido, d.categoria,
                          p.nome AS parlamentar_nome
                FROM despesas d
                JOIN parlamentares p ON d.parlamentar_id = p.id
                WHERE d.url_documento IS NOT NULL AND d.url_documento != ''
                  AND d.categoria ILIKE '%aliment%'
                  AND NOT EXISTS (
                      SELECT 1 FROM suspeitas s WHERE s.despesa_id = d.id AND s.classificador = 'ocr_recibo'
                  )
                ORDER BY d.valor_liquido DESC NULLS LAST
                LIMIT 50"""
            )

            context.log.info(f"Analisando {len(rows)} recibos...")
            irregulares = 0
            for row in rows:
                result = await process_receipt(row["url_documento"])
                if not result or result.get("needs_vision_ocr"):
                    continue
                if result.get("tem_alcool") or result.get("irregularidades"):
                    await pool.execute(
                        """INSERT INTO suspeitas (despesa_id, classificador, probabilidade, detalhes)
                        VALUES ($1, 'ocr_recibo', 0.8, $2::jsonb)
                        ON CONFLICT DO NOTHING""",
                        row["id"], json.dumps(result, ensure_ascii=False, default=str),
                    )
                    irregulares += 1

            context.log.info(f"{irregulares} irregularidades em {len(rows)} recibos")
        finally:
            await pool.close()

    _run_async(run())

@asset(
    group_name="rag",
    deps=[despesas_camara, senado],
    description="Embeddings para busca semântica (despesas, contratos, licitações, emendas, votações, proposições)",
)
def embeddings(context: AssetExecutionContext):
    async def run():
        from app.services.embeddings import generate_embeddings_batch

        BATCH_SIZE = 32

        async def gerar_embeddings_tipo(pool, tipo: str, query: str, to_text_fn):
            rows = await pool.fetch(query)
            context.log.info(f"{tipo}: {len(rows)} registros sem embedding")
            total = 0
            for i in range(0, len(rows), BATCH_SIZE):
                batch = rows[i:i + BATCH_SIZE]
                texts = [to_text_fn(r) for r in batch]
                embs = await generate_embeddings_batch(texts)
                for row, text, emb in zip(batch, texts, embs, strict=False):
                    if emb is None:
                        continue
                    await pool.execute(
                        """INSERT INTO embeddings (tipo, referencia_id, conteudo_texto, embedding)
                        VALUES ($1, $2, $3, $4::vector)
                        ON CONFLICT (tipo, referencia_id) DO NOTHING""",
                        tipo, row["id"], text, json.dumps(emb),
                    )
                    total += 1
                await asyncio.sleep(1)
            context.log.info(f"{tipo}: {total} embeddings gerados")
            return total

        pool = await _create_pool()
        try:
            total = 0

            total += await gerar_embeddings_tipo(
                pool, "despesa",
                """SELECT d.id, d.ano, d.mes, d.categoria, d.fornecedor, d.valor_liquido,
                          p.nome AS parlamentar_nome, p.partido, p.uf
                FROM despesas d
                JOIN parlamentares p ON d.parlamentar_id = p.id
                WHERE NOT EXISTS (
                    SELECT 1 FROM embeddings e WHERE e.tipo = 'despesa' AND e.referencia_id = d.id
                )
                ORDER BY d.id""",
                lambda r: " ".join(p for p in [
                    f"{r['parlamentar_nome']} ({r['partido']}/{r['uf']})",
                    f"gastou R$ {r['valor_liquido']}" if r["valor_liquido"] else "",
                    f"em {r['categoria']}" if r["categoria"] else "",
                    f"no fornecedor {r['fornecedor']}" if r["fornecedor"] else "",
                    f"em {r['mes']}/{r['ano']}" if r["ano"] else "",
                ] if p),
            )

            total += await gerar_embeddings_tipo(
                pool, "contrato",
                """SELECT id, orgao_nome, fornecedor_nome, objeto, modalidade_licitacao,
                          valor_inicial, valor_final, situacao
                FROM contratos
                WHERE NOT EXISTS (
                    SELECT 1 FROM embeddings e WHERE e.tipo = 'contrato' AND e.referencia_id = contratos.id
                )
                ORDER BY id""",
                lambda r: " ".join(p for p in [
                    f"Contrato {r['orgao_nome'] or ''}",
                    f"com {r['fornecedor_nome']}" if r["fornecedor_nome"] else "",
                    f"objeto: {(r['objeto'] or '')[:300]}",
                    f"modalidade {r['modalidade_licitacao']}" if r["modalidade_licitacao"] else "",
                    f"valor R$ {r['valor_final']}" if r["valor_final"] else "",
                    f"situação {r['situacao']}" if r["situacao"] else "",
                ] if p),
            )

            total += await gerar_embeddings_tipo(
                pool, "licitacao",
                """SELECT id, orgao_nome, modalidade, objeto, situacao, valor_estimado
                FROM licitacoes
                WHERE NOT EXISTS (
                    SELECT 1 FROM embeddings e WHERE e.tipo = 'licitacao' AND e.referencia_id = licitacoes.id
                )
                ORDER BY id""",
                lambda r: " ".join(p for p in [
                    f"Licitação {r['modalidade'] or ''} {r['orgao_nome'] or ''}",
                    f"objeto: {(r['objeto'] or '')[:300]}",
                    f"situação {r['situacao']}" if r["situacao"] else "",
                    f"valor estimado R$ {r['valor_estimado']}" if r["valor_estimado"] else "",
                ] if p),
            )

            total += await gerar_embeddings_tipo(
                pool, "emenda",
                """SELECT id, autor, tipo_emenda, localidade_gasto, funcao, subfuncao,
                          valor_empenhado, valor_pago, ano
                FROM emendas
                WHERE NOT EXISTS (
                    SELECT 1 FROM embeddings e WHERE e.tipo = 'emenda' AND e.referencia_id = emendas.id
                )
                ORDER BY id""",
                lambda r: " ".join(p for p in [
                    f"Emenda {r['tipo_emenda'] or ''} de {r['autor'] or ''}",
                    f"para {r['localidade_gasto']}" if r["localidade_gasto"] else "",
                    f"área {r['funcao']}" if r["funcao"] else "",
                    f"subfunção {r['subfuncao']}" if r["subfuncao"] else "",
                    f"empenhado R$ {r['valor_empenhado']}" if r["valor_empenhado"] else "",
                    f"em {r['ano']}" if r["ano"] else "",
                ] if p),
            )

            total += await gerar_embeddings_tipo(
                pool, "proposicao",
                """SELECT id, sigla_tipo, numero, ano, ementa, autor, casa
                FROM proposicoes
                WHERE NOT EXISTS (
                    SELECT 1 FROM embeddings e WHERE e.tipo = 'proposicao' AND e.referencia_id = proposicoes.id
                )
                ORDER BY id""",
                lambda r: " ".join(p for p in [
                    f"{r['sigla_tipo']} {r['numero']}/{r['ano']}" if r["sigla_tipo"] else "",
                    f"({r['casa']})" if r["casa"] else "",
                    r["ementa"] or "",
                    f"autor: {r['autor']}" if r["autor"] else "",
                ] if p),
            )

            total += await gerar_embeddings_tipo(
                pool, "votacao",
                """SELECT v.id, v.descricao, v.sigla_tipo, v.numero, v.ano, v.casa,
                          v.aprovada, v.votos_sim, v.votos_nao,
                          p.ementa AS proposicao_ementa
                FROM votacoes v
                LEFT JOIN proposicoes p ON v.proposicao_id = p.id
                WHERE NOT EXISTS (
                    SELECT 1 FROM embeddings e WHERE e.tipo = 'votacao' AND e.referencia_id = v.id
                )
                ORDER BY v.id""",
                lambda r: " ".join(p for p in [
                    f"Votação {r['casa']}",
                    f"{r['sigla_tipo']} {r['numero']}/{r['ano']}" if r["sigla_tipo"] else "",
                    f"{'Aprovada' if r['aprovada'] else 'Rejeitada'}" if r["aprovada"] is not None else "",
                    f"({r['votos_sim']} sim, {r['votos_nao']} não)" if r["votos_sim"] else "",
                    (r["descricao"] or "")[:200],
                    (r["proposicao_ementa"] or "")[:300],
                ] if p),
            )

            total += await gerar_embeddings_tipo(
                pool, "viagem",
                """SELECT id, orgao_nome, viajante_nome, cargo, destino, motivo,
                          urgente, data_ida, valor_passagens, valor_diarias
                FROM viagens
                WHERE NOT EXISTS (
                    SELECT 1 FROM embeddings e WHERE e.tipo = 'viagem' AND e.referencia_id = viagens.id
                )
                ORDER BY id""",
                lambda r: " ".join(p for p in [
                    f"Viagem {r['orgao_nome'] or ''}",
                    f"viajante {r['viajante_nome']}" if r["viajante_nome"] else "",
                    f"({r['cargo']})" if r["cargo"] else "",
                    f"para {r['destino']}" if r["destino"] else "",
                    f"motivo: {(r['motivo'] or '')[:200]}",
                    "URGENTE" if r["urgente"] else "",
                    f"passagens R$ {r['valor_passagens']}" if r["valor_passagens"] else "",
                    f"diárias R$ {r['valor_diarias']}" if r["valor_diarias"] else "",
                    f"em {r['data_ida']}" if r["data_ida"] else "",
                ] if p),
            )

            total += await gerar_embeddings_tipo(
                pool, "cpgf",
                """SELECT id, orgao_nome, portador_nome, favorecido_nome,
                          valor, data_transacao, mes_extrato, ano_extrato
                FROM cpgf
                WHERE NOT EXISTS (
                    SELECT 1 FROM embeddings e WHERE e.tipo = 'cpgf' AND e.referencia_id = cpgf.id
                )
                ORDER BY id""",
                lambda r: " ".join(p for p in [
                    f"Cartão corporativo {r['orgao_nome'] or ''}",
                    f"portador {r['portador_nome']}" if r["portador_nome"] else "",
                    f"no estabelecimento {r['favorecido_nome']}" if r["favorecido_nome"] else "",
                    f"R$ {r['valor']}" if r["valor"] else "",
                    f"em {r['data_transacao']}" if r["data_transacao"] else f"em {r['mes_extrato']}/{r['ano_extrato']}" if r["ano_extrato"] else "",
                ] if p),
            )

            total += await gerar_embeddings_tipo(
                pool, "sancao",
                """SELECT id, tipo, nome, cpf_cnpj, orgao_sancionador,
                          fundamentacao_legal, data_inicio, data_fim
                FROM sancoes
                WHERE NOT EXISTS (
                    SELECT 1 FROM embeddings e WHERE e.tipo = 'sancao' AND e.referencia_id = sancoes.id
                )
                ORDER BY id""",
                lambda r: " ".join(p for p in [
                    f"Sanção {r['tipo']}",
                    f"empresa {r['nome']}" if r["nome"] else "",
                    f"CNPJ {r['cpf_cnpj']}" if r["cpf_cnpj"] else "",
                    f"por {r['orgao_sancionador']}" if r["orgao_sancionador"] else "",
                    f"fundamento: {(r['fundamentacao_legal'] or '')[:200]}",
                    f"de {r['data_inicio']}" if r["data_inicio"] else "",
                    f"até {r['data_fim']}" if r["data_fim"] else "",
                ] if p),
            )

            context.log.info(f"Total geral: {total} embeddings gerados")
        finally:
            await pool.close()

    _run_async(run())

@asset(
    group_name="rag",
    description="Embeddings do glossario de termos (RAG conceitual da Calunga)",
)
def embeddings_glossario(context: AssetExecutionContext):
    """Gera embeddings BGE-M3 para termos do glossario_termos sem embedding.

    Roda raramente (glossario e semi-estatico, ~20 termos). Grava o vetor
    direto em glossario_termos.embedding, diferente do asset embeddings
    que usa a tabela generica embeddings(tipo, referencia_id, ...).
    """
    async def run():
        from app.services.embeddings import generate_embeddings_batch

        pool = await _create_pool()
        try:
            rows = await pool.fetch(
                "SELECT id, termo, definicao FROM glossario_termos WHERE embedding IS NULL"
            )
            context.log.info(f"glossario: {len(rows)} termos sem embedding")
            if not rows:
                return

            texts = [f"{r['termo']}: {r['definicao']}" for r in rows]
            embs = await generate_embeddings_batch(texts)
            total = 0
            for row, emb in zip(rows, embs, strict=False):
                if emb is None:
                    continue
                await pool.execute(
                    "UPDATE glossario_termos SET embedding = $1::vector, atualizado_em = now() WHERE id = $2",
                    json.dumps(emb), row["id"],
                )
                total += 1
            context.log.info(f"glossario: {total} embeddings gerados")
        finally:
            await pool.close()

    _run_async(run())

@asset(group_name="alertas", deps=[suspeitas], description="Publica votações importantes e emendas Pix no feed")
def feed_eventos_dagster(context: AssetExecutionContext):
    async def run():
        from app.queries.feed import publicar_evento
        from app.schemas.feed import Acao, Ator, Contexto, Objeto, Severidade
        from app.services.feed_enrichment import (
            construir_dados_ricos,
            formatar_brl,
            link_camara_proposicao,
            link_senado_materia,
            link_siop_emendas,
        )

        pool = await _create_pool(max_size=2)
        try:
            total = 0

            votacoes = await pool.fetch(
                """SELECT v.id, v.descricao, v.sigla_tipo, v.numero, v.ano, v.casa,
                          v.aprovada, v.votos_sim, v.votos_nao, v.votos_abstencao,
                          v.data_hora, v.orgao,
                          p.ementa AS proposicao_ementa,
                          p.autor AS proposicao_autor,
                          p.tema AS proposicao_tema,
                          p.id_externo AS proposicao_id_externo,
                          p.url_inteiro_teor
                FROM votacoes v
                LEFT JOIN proposicoes p ON v.proposicao_id = p.id
                WHERE v.sigla_tipo IN ('PEC', 'PLP', 'MPV', 'PL')
                  AND v.data_hora >= NOW() - INTERVAL '7 days'
                  AND NOT EXISTS (
                      SELECT 1 FROM feed_eventos f
                      WHERE f.referencia_tipo = 'votacao' AND f.referencia_id = v.id
                  )
                ORDER BY v.data_hora DESC
                LIMIT 50"""
            )
            for v in votacoes:
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

                ator = Ator(
                    nome=casa_nome,
                    papel="Plenário" if not v["orgao"] else v["orgao"],
                )
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

                links = []
                if v["casa"] == "camara":
                    links.append(link_camara_proposicao(v["sigla_tipo"], v["numero"], v["ano"]))
                else:
                    links.append(link_senado_materia(v["proposicao_id_externo"]))
                if v["url_inteiro_teor"]:
                    from app.schemas.feed import LinkFeed
                    links.append(LinkFeed(
                        label="Inteiro teor da proposição",
                        url=v["url_inteiro_teor"],
                        tipo="documento",
                    ))

                severidade = (
                    Severidade.ATENCAO
                    if v["sigla_tipo"] in ("PEC", "MPV")
                    else Severidade.INFORMATIVO
                )

                dados_ricos = construir_dados_ricos(
                    ator=ator,
                    acao=acao,
                    objeto=objeto,
                    contexto=contexto,
                    links=links,
                    severidade=severidade,
                )

                await publicar_evento(
                    pool,
                    tipo="votacao",
                    categoria="congresso",
                    origem="dagster",
                    titulo=titulo,
                    descricao=descricao[:500],
                    dados=dados_ricos,
                    referencia_tipo="votacao",
                    referencia_id=v["id"],
                    relevancia=0.8 if v["sigla_tipo"] in ("PEC", "MPV") else 0.6,
                )
                total += 1

            emendas = await pool.fetch(
                """SELECT id, autor, tipo_emenda, localidade_gasto, funcao, subfuncao,
                          valor_empenhado, valor_pago, valor_liquidado, ano, numero
                FROM emendas
                WHERE tipo_emenda ILIKE '%Transferências Especiais%'
                  AND created_at >= NOW() - INTERVAL '7 days'
                  AND NOT EXISTS (
                      SELECT 1 FROM feed_eventos f
                      WHERE f.referencia_tipo = 'emenda' AND f.referencia_id = emendas.id
                  )
                ORDER BY valor_empenhado DESC NULLS LAST
                LIMIT 50"""
            )
            for e in emendas:
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
                    ator=ator,
                    acao=acao,
                    objeto=objeto,
                    contexto=contexto,
                    links=[link_siop_emendas()],
                    severidade=Severidade.ATENCAO if valor >= 1_000_000 else Severidade.INFORMATIVO,
                )

                await publicar_evento(
                    pool,
                    tipo="emenda_pix",
                    categoria="governo_federal",
                    origem="dagster",
                    titulo=titulo,
                    descricao=descricao,
                    dados=dados_ricos,
                    referencia_tipo="emenda",
                    referencia_id=e["id"],
                    relevancia=0.7,
                )
                total += 1

            context.log.info(f"Feed: {total} novos eventos publicados")
        finally:
            await pool.close()

    _run_async(run())

ORGAOS_FEDERAIS = {
    "20000": "Presidência da República",
    "20301": "Casa Civil",
    "20401": "Secretaria de Governo",
    "30000": "Ministério da Justiça e Segurança Pública",
    "22000": "Ministério da Agricultura",
    "25000": "Ministério da Fazenda",
    "26000": "Ministério da Educação",
    "36000": "Ministério da Saúde",
    "39000": "Ministério da Infraestrutura",
    "52000": "Ministério da Defesa",
}

@asset(retry_policy=_API_RETRY_POLICY, group_name="federal", description="Gastos do cartão corporativo (CPGF) do executivo federal")
def cpgf_federal(context: AssetExecutionContext):
    async def run():
        from datetime import date

        import httpx

        from app.config import settings
        from app.queries.federal import upsert_cpgf
        from app.services.transparencia import TransparenciaService

        def _clean_doc(val):
            if not val:
                return None
            cleaned = "".join(c for c in str(val) if c.isdigit())
            return cleaned or None

        def _parse_valor(val):

            if val is None:
                return None
            if isinstance(val, (int, float)):
                return float(val)
            try:
                return float(str(val).replace(".", "").replace(",", "."))
            except (ValueError, TypeError):
                return None

        ano_atual = date.today().year
        anos = _anos_federais_janela()
        pool = await _create_pool()
        try:
            async with httpx.AsyncClient(
                base_url="https://api.portaldatransparencia.gov.br/api-de-dados",
                timeout=30.0,
                headers={"chave-api-dados": settings.transparencia_api_token, "Accept": "application/json"},
            ) as client:
                service = TransparenciaService(client)
                total = 0
                for ano in anos:
                    for mes in range(1, 13):
                        if ano == ano_atual and mes > date.today().month:
                            break
                        mes_str = f"{mes:02d}/{ano}"
                        for codigo_orgao in ORGAOS_FEDERAIS:
                            try:
                                records = await service.buscar_cpgf(mes_str, mes_str, codigo_orgao)
                            except Exception as e:
                                context.log.warning(f"Erro CPGF {codigo_orgao} {mes_str}: {e}")
                                continue
                            for r in records:
                                unidade = r.get("unidadeGestora") or {}
                                orgao_unidade = unidade.get("orgaoVinculado") or unidade.get("orgaoMaximo") or {}
                                estabelecimento = r.get("estabelecimento") or {}
                                portador = r.get("portador") or {}
                                id_ext = f"cpgf-{r.get('id', '')}-{codigo_orgao}-{mes}-{ano}"
                                try:
                                    await upsert_cpgf(
                                        pool,
                                        id_externo=id_ext,
                                        orgao_codigo=str(orgao_unidade.get("codigo") or codigo_orgao),
                                        orgao_nome=orgao_unidade.get("nome") or ORGAOS_FEDERAIS.get(codigo_orgao),
                                        unidade_gestora_codigo=str(unidade.get("codigo", "")),
                                        unidade_gestora_nome=unidade.get("nome"),
                                        portador_nome=portador.get("nome"),
                                        portador_cpf=_clean_doc(portador.get("cpfFormatado") or portador.get("numeroInscricaoSocial")),
                                        tipo_cartao=(r.get("tipoCartao") or {}).get("descricao"),
                                        transacao=None,
                                        cnpj_cpf_favorecido=_clean_doc(estabelecimento.get("cnpjFormatado") or estabelecimento.get("cpfFormatado")),
                                        favorecido_nome=estabelecimento.get("nome") or estabelecimento.get("razaoSocialReceita"),
                                        valor=_parse_valor(r.get("valorTransacao")),
                                        data_transacao=r.get("dataTransacao"),
                                        mes_extrato=mes,
                                        ano_extrato=ano,
                                    )
                                    total += 1
                                except Exception as e:
                                    context.log.warning(f"Erro upsert CPGF {id_ext}: {e}")
                    context.log.info(f"CPGF {ano}: {total} transações acumuladas")
                context.log.info(f"Total: {total} transações CPGF")
        finally:
            await pool.close()

    _run_async(run())

@asset(retry_policy=_API_RETRY_POLICY, group_name="federal", description="Execução orçamentária federal (empenhos, liquidações, pagamentos)")
def despesas_federais(context: AssetExecutionContext):
    async def run():

        import httpx

        from app.config import settings
        from app.queries.federal import upsert_despesa_orcamentaria
        from app.services.transparencia import TransparenciaService

        pool = await _create_pool()
        try:
            async with httpx.AsyncClient(
                base_url="https://api.portaldatransparencia.gov.br/api-de-dados",
                timeout=30.0,
                headers={"chave-api-dados": settings.transparencia_api_token, "Accept": "application/json"},
            ) as client:
                service = TransparenciaService(client)
                total = 0
                for ano in _anos_federais_janela():
                    for codigo_orgao, nome_orgao in ORGAOS_FEDERAIS.items():
                        context.log.info(f"Buscando despesas {nome_orgao} {ano}...")
                        try:
                            records = await service.buscar_despesas_orgao(ano, codigo_orgao)
                        except Exception as e:
                            context.log.warning(f"Erro despesas {nome_orgao} {ano}: {e}")
                            continue
                        for r in records:
                            id_ext = f"desp-fed-{r.get('codigoOrgao', '')}-{codigo_orgao}-{ano}"
                            await upsert_despesa_orcamentaria(
                                pool,
                                id_externo=id_ext,
                                ano=ano,
                            orgao_superior_codigo=r.get("codigoOrgaoSuperior"),
                            orgao_superior_nome=r.get("orgaoSuperior"),
                            orgao_vinculado_codigo=r.get("codigoOrgao"),
                            orgao_vinculado_nome=r.get("orgao"),
                            unidade_gestora_codigo=None,
                            unidade_gestora_nome=None,
                            funcao=None,
                            subfuncao=None,
                            programa=None,
                            acao=None,
                            categoria_economica=None,
                            grupo_despesa=None,
                            elemento_despesa=None,
                            modalidade_licitacao=None,
                            favorecido_nome=None,
                            favorecido_cnpj_cpf=None,
                            valor_empenhado=r.get("empenhado"),
                            valor_liquidado=r.get("liquidado"),
                            valor_pago=r.get("pago"),
                            valor_resto_pago=None,
                        )
                        total += 1
                context.log.info(f"Total: {total} despesas orçamentárias federais")
        finally:
            await pool.close()

    _run_async(run())

@asset(retry_policy=_API_RETRY_POLICY, group_name="federal", description="Contratos do executivo federal")
def contratos_federais(context: AssetExecutionContext):
    async def run():

        import httpx

        from app.config import settings
        from app.queries.federal import upsert_contrato
        from app.services.transparencia import TransparenciaService

        pool = await _create_pool()
        try:
            async with httpx.AsyncClient(
                base_url="https://api.portaldatransparencia.gov.br/api-de-dados",
                timeout=30.0,
                headers={"chave-api-dados": settings.transparencia_api_token, "Accept": "application/json"},
            ) as client:
                service = TransparenciaService(client)
                total = 0
                for ano in _anos_federais_janela():
                    data_ini = f"01/01/{ano}"
                    data_fim_str = f"31/12/{ano}"
                    for codigo_orgao, nome_orgao in ORGAOS_FEDERAIS.items():
                        context.log.info(f"Buscando contratos {nome_orgao} {ano}...")
                        try:
                            records = await service.buscar_contratos(codigo_orgao, data_ini, data_fim_str)
                        except Exception as e:
                            context.log.warning(f"Erro contratos {nome_orgao} {ano}: {e}")
                            continue
                        for r in records:
                            fornecedor = r.get("fornecedor") or {}
                            id_ext = f"contrato-{r.get('id', '')}-{codigo_orgao}"
                            await upsert_contrato(
                                pool,
                                id_externo=id_ext,
                                orgao_codigo=codigo_orgao,
                                orgao_nome=nome_orgao,
                                unidade_gestora_codigo=str(r.get("unidadeGestora", {}).get("codigo", "")),
                                unidade_gestora_nome=r.get("unidadeGestora", {}).get("nome"),
                                fornecedor_nome=fornecedor.get("nome") or fornecedor.get("razaoSocialReceita"),
                                fornecedor_cnpj_cpf=fornecedor.get("cnpjFormatado") or fornecedor.get("cpfFormatado"),
                                objeto=r.get("objeto"),
                                numero=r.get("numero"),
                                modalidade_licitacao=r.get("modalidadeCompra"),
                                situacao=r.get("situacaoContrato"),
                                valor_inicial=r.get("valorInicial"),
                                valor_final=r.get("valorFinal"),
                                valor_acumulado=r.get("valorAcumulado"),
                                data_inicio=r.get("dataInicioVigencia"),
                                data_fim=r.get("dataFimVigencia"),
                                data_publicacao=r.get("dataPublicacaoDOU"),
                            )
                            total += 1
                context.log.info(f"Total: {total} contratos federais")
        finally:
            await pool.close()

    _run_async(run())

@asset(retry_policy=_API_RETRY_POLICY, group_name="federal", description="Licitações do executivo federal")
def licitacoes_federais(context: AssetExecutionContext):
    async def run():
        import calendar
        from datetime import date

        import httpx

        from app.config import settings
        from app.queries.federal import upsert_licitacao
        from app.services.transparencia import TransparenciaService

        ano_atual = date.today().year
        anos = _anos_federais_janela()
        pool = await _create_pool()
        try:
            async with httpx.AsyncClient(
                base_url="https://api.portaldatransparencia.gov.br/api-de-dados",
                timeout=30.0,
                headers={"chave-api-dados": settings.transparencia_api_token, "Accept": "application/json"},
            ) as client:
                service = TransparenciaService(client)
                total = 0
                for codigo_orgao, nome_orgao in ORGAOS_FEDERAIS.items():
                    total_orgao = 0
                    for ano in anos:
                        for mes in range(1, 13):

                            if ano == ano_atual and mes > date.today().month:
                                break
                            ultimo_dia = calendar.monthrange(ano, mes)[1]
                            data_ini = f"01/{mes:02d}/{ano}"
                            data_fim_str = f"{ultimo_dia:02d}/{mes:02d}/{ano}"
                            try:
                                records = await service.buscar_licitacoes(codigo_orgao, data_ini, data_fim_str)
                            except Exception as e:
                                context.log.warning(f"Erro licitações {nome_orgao} {mes:02d}/{ano}: {e}")
                                continue
                            for r in records:
                                licitacao_obj = r.get("licitacao") or {}
                                id_ext = f"licit-{r.get('id', '')}-{codigo_orgao}"
                                try:
                                    await upsert_licitacao(
                                        pool,
                                        id_externo=id_ext,
                                        orgao_codigo=codigo_orgao,
                                        orgao_nome=nome_orgao,
                                        unidade_gestora_codigo=str(r.get("unidadeGestora", {}).get("codigo", "")),
                                        unidade_gestora_nome=r.get("unidadeGestora", {}).get("nome"),
                                        modalidade=r.get("modalidadeLicitacao"),
                                        numero=licitacao_obj.get("numero"),
                                        objeto=licitacao_obj.get("objeto"),
                                        situacao=r.get("situacaoCompra"),
                                        valor_estimado=r.get("valor"),
                                        valor_homologado=None,
                                        data_abertura=r.get("dataAbertura"),
                                        data_resultado=r.get("dataResultadoCompra"),
                                        data_publicacao=r.get("dataPublicacao"),
                                    )
                                    total += 1
                                    total_orgao += 1
                                except Exception as e:
                                    context.log.warning(f"Erro upsert licitação {id_ext}: {e}")
                    context.log.info(f"{nome_orgao}: {total_orgao} licitações")
                context.log.info(f"Total: {total} licitações federais")
        finally:
            await pool.close()

    _run_async(run())

@asset(retry_policy=_API_RETRY_POLICY, group_name="federal", description="Viagens a serviço do executivo federal")
def viagens_federais(context: AssetExecutionContext):
    async def run():
        import calendar
        from datetime import date

        import httpx

        from app.config import settings
        from app.queries.federal import upsert_viagem
        from app.services.transparencia import TransparenciaService

        ano_atual = date.today().year
        pool = await _create_pool()
        try:
            async with httpx.AsyncClient(
                base_url="https://api.portaldatransparencia.gov.br/api-de-dados",
                timeout=30.0,
                headers={"chave-api-dados": settings.transparencia_api_token, "Accept": "application/json"},
            ) as client:
                service = TransparenciaService(client)
                total = 0
                for ano in _anos_federais_janela():
                    for codigo_orgao, nome_orgao in ORGAOS_FEDERAIS.items():
                        context.log.info(f"Buscando viagens {nome_orgao} {ano}...")
                        for mes in range(1, 13):

                            if ano == ano_atual and mes > date.today().month:
                                break
                            ultimo_dia = calendar.monthrange(ano, mes)[1]
                            data_ini = f"01/{mes:02d}/{ano}"
                            data_fim_str = f"{ultimo_dia:02d}/{mes:02d}/{ano}"
                            try:
                                records = await service.buscar_viagens(codigo_orgao, data_ini, data_fim_str)
                            except Exception as e:
                                context.log.warning(f"Erro viagens {nome_orgao} {mes:02d}/{ano}: {e}")
                                continue
                            for r in records:
                                viagem = r.get("viagem") or {}
                                beneficiario = r.get("beneficiario") or {}
                                cargo_obj = r.get("cargo") or {}
                                id_ext = f"viagem-{r.get('id', '')}-{codigo_orgao}"
                                await upsert_viagem(
                                    pool,
                                    id_externo=id_ext,
                                    orgao_codigo=codigo_orgao,
                                    orgao_nome=nome_orgao,
                                    viajante_nome=beneficiario.get("nome"),
                                    viajante_cpf=beneficiario.get("cpfFormatado"),
                                    cargo=cargo_obj.get("descricao"),
                                    destino=None,
                                    motivo=viagem.get("motivo"),
                                    urgente=viagem.get("urgenciaViagem") == "Sim",
                                    data_ida=r.get("dataInicioAfastamento"),
                                    data_volta=r.get("dataFimAfastamento"),
                                    valor_passagens=r.get("valorTotalPassagem"),
                                    valor_diarias=r.get("valorTotalDiarias"),
                                    valor_outros=r.get("valorTotalRestituicao"),
                                )
                                total += 1
                context.log.info(f"Total: {total} viagens federais")
        finally:
            await pool.close()

    _run_async(run())

@asset(retry_policy=_API_RETRY_POLICY, group_name="federal", description="Emendas parlamentares (execução orçamentária)")
def emendas_parlamentares(context: AssetExecutionContext):
    async def run():

        import httpx

        from app.config import settings
        from app.queries.federal import upsert_emenda
        from app.services.transparencia import TransparenciaService

        pool = await _create_pool()
        try:
            async with httpx.AsyncClient(
                base_url="https://api.portaldatransparencia.gov.br/api-de-dados",
                timeout=30.0,
                headers={"chave-api-dados": settings.transparencia_api_token, "Accept": "application/json"},
            ) as client:
                service = TransparenciaService(client)
                total = 0
                for ano in _anos_federais_janela():
                    context.log.info(f"Buscando emendas {ano}...")
                    try:
                        records = await service.buscar_emendas(ano)
                    except Exception as e:
                        context.log.warning(f"Erro emendas {ano}: {e}")
                        continue
                    for r in records:
                        id_ext = f"emenda-{r.get('codigoEmenda', '')}-{ano}"
                        await upsert_emenda(
                            pool,
                            id_externo=id_ext,
                            ano=ano,
                            autor=r.get("nomeAutor") or r.get("autor"),
                            tipo_emenda=r.get("tipoEmenda"),
                            numero=r.get("numeroEmenda"),
                            localidade_gasto=r.get("localidadeDoGasto"),
                            funcao=r.get("funcao"),
                            subfuncao=r.get("subfuncao"),
                            valor_empenhado=r.get("valorEmpenhado"),
                            valor_liquidado=r.get("valorLiquidado"),
                            valor_pago=r.get("valorPago"),
                        )
                        total += 1
                context.log.info(f"Total: {total} emendas parlamentares")
        finally:
            await pool.close()

    _run_async(run())

ESTADOS_IBGE = {
    "12": "AC", "27": "AL", "13": "AM", "16": "AP", "29": "BA", "23": "CE",
    "53": "DF", "32": "ES", "52": "GO", "21": "MA", "31": "MG", "50": "MS",
    "51": "MT", "15": "PA", "25": "PB", "26": "PE", "22": "PI", "41": "PR",
    "33": "RJ", "24": "RN", "11": "RO", "14": "RR", "43": "RS", "42": "SC",
    "28": "SE", "35": "SP", "17": "TO",
}

CAPITAIS_IBGE = {
    "1200401": "Rio Branco", "2704302": "Maceió", "1302603": "Manaus",
    "1600303": "Macapá", "2927408": "Salvador", "2304400": "Fortaleza",
    "5300108": "Brasília", "3205309": "Vitória", "5208707": "Goiânia",
    "2111300": "São Luís", "3106200": "Belo Horizonte", "5002704": "Campo Grande",
    "5103403": "Cuiabá", "1501402": "Belém", "2507507": "João Pessoa",
    "2611606": "Recife", "2211001": "Teresina", "4106902": "Curitiba",
    "3304557": "Rio de Janeiro", "2408102": "Natal", "1100205": "Porto Velho",
    "1400100": "Boa Vista", "4314902": "Porto Alegre", "4205407": "Florianópolis",
    "2800308": "Aracaju", "3550308": "São Paulo", "1721000": "Palmas",
}

@asset(retry_policy=_API_RETRY_POLICY, group_name="fiscal", description="Dados fiscais SICONFI dos 27 estados (RREO + RGF)")
def fiscal_estados(context: AssetExecutionContext):
    async def run():
        from datetime import date

        from app.queries.entes import buscar_ente_por_ibge
        from app.queries.federal import upsert_dado_fiscal
        from app.services.siconfi import SiconfiService

        pool = await _create_pool()
        try:
            service = SiconfiService()
            ano = date.today().year
            total = 0
            for ibge, uf in ESTADOS_IBGE.items():
                ente = await buscar_ente_por_ibge(pool, ibge)
                if not ente:
                    continue

                for periodo in range(1, 7):
                    try:
                        records = await service.buscar_rreo(ibge, ano, periodo)
                        for r in records:
                            await upsert_dado_fiscal(
                                pool, ente_id=ente["id"],
                                exercicio=r.get("exercicio", ano),
                                periodo=r.get("periodo", periodo),
                                demonstrativo="RREO",
                                anexo=r.get("anexo", ""),
                                coluna=r.get("coluna"),
                                rotulo=r.get("rotulo"),
                                valor=r.get("valor"),
                            )
                            total += 1
                    except Exception as e:
                        context.log.warning(f"Erro RREO {uf} {ano}/{periodo}: {e}")

                for periodo in range(1, 4):
                    try:
                        records = await service.buscar_rgf(ibge, ano, periodo)
                        for r in records:
                            await upsert_dado_fiscal(
                                pool, ente_id=ente["id"],
                                exercicio=r.get("exercicio", ano),
                                periodo=r.get("periodo", periodo),
                                demonstrativo="RGF",
                                anexo=r.get("anexo", ""),
                                coluna=r.get("coluna"),
                                rotulo=r.get("rotulo"),
                                valor=r.get("valor"),
                            )
                            total += 1
                    except Exception as e:
                        context.log.warning(f"Erro RGF {uf} {ano}/{periodo}: {e}")

            await service.close()
            context.log.info(f"Total: {total} registros fiscais estaduais ({ano})")
        finally:
            await pool.close()

    _run_async(run())

@asset(retry_policy=_API_RETRY_POLICY, group_name="fiscal", description="Dados fiscais SICONFI das 27 capitais (RREO + RGF)")
def fiscal_capitais(context: AssetExecutionContext):
    async def run():
        from datetime import date

        from app.queries.entes import buscar_ente_por_ibge
        from app.queries.federal import upsert_dado_fiscal
        from app.services.siconfi import SiconfiService

        pool = await _create_pool()
        try:
            service = SiconfiService()
            ano = date.today().year
            total = 0
            for ibge, nome in CAPITAIS_IBGE.items():
                ente = await buscar_ente_por_ibge(pool, ibge)
                if not ente:
                    continue

                for periodo in range(1, 7):
                    try:
                        records = await service.buscar_rreo(ibge, ano, periodo)
                        for r in records:
                            await upsert_dado_fiscal(
                                pool, ente_id=ente["id"],
                                exercicio=r.get("exercicio", ano),
                                periodo=r.get("periodo", periodo),
                                demonstrativo="RREO",
                                anexo=r.get("anexo", ""),
                                coluna=r.get("coluna"),
                                rotulo=r.get("rotulo"),
                                valor=r.get("valor"),
                            )
                            total += 1
                    except Exception as e:
                        context.log.warning(f"Erro RREO {nome} {ano}/{periodo}: {e}")

                for periodo in range(1, 4):
                    try:
                        records = await service.buscar_rgf(ibge, ano, periodo, esfera="E")
                        for r in records:
                            await upsert_dado_fiscal(
                                pool, ente_id=ente["id"],
                                exercicio=r.get("exercicio", ano),
                                periodo=r.get("periodo", periodo),
                                demonstrativo="RGF",
                                anexo=r.get("anexo", ""),
                                coluna=r.get("coluna"),
                                rotulo=r.get("rotulo"),
                                valor=r.get("valor"),
                            )
                            total += 1
                    except Exception as e:
                        context.log.warning(f"Erro RGF {nome} {ano}/{periodo}: {e}")

            await service.close()
            context.log.info(f"Total: {total} registros fiscais municipais (capitais)")
        finally:
            await pool.close()

    _run_async(run())

@asset(group_name="executivo", description="Governadores dos 27 estados + prefeitos das 27 capitais")
def governadores_prefeitos(context: AssetExecutionContext):
    """Insere governadores e prefeitos com base nos dados do TSE (eleições 2022/2024)."""
    async def run():
        from app.queries.entes import buscar_ente_por_ibge
        from app.queries.parlamentares import upsert_parlamentar

        pool = await _create_pool()
        try:

            govs = await pool.fetch(
                """SELECT DISTINCT ON (uf)
                    nome, nome_urna, cpf, partido, uf, ano_eleicao
                FROM candidatos_tse
                WHERE cargo ILIKE '%governador%'
                  AND situacao ILIKE '%eleit%'
                ORDER BY uf, ano_eleicao DESC"""
            )
            for g in govs:
                await buscar_ente_por_ibge(pool, "")

                ente_row = await pool.fetchrow(
                    "SELECT id FROM entes WHERE tipo = 'estado' AND uf = $1", g["uf"]
                )
                await upsert_parlamentar(
                    pool,
                    id_externo=f"gov-{g['uf']}-{g['ano_eleicao']}",
                    tipo="governador",
                    nome=g["nome"],
                    nome_civil=g["nome"],
                    cpf=g["cpf"],
                    partido=g["partido"],
                    uf=g["uf"],
                    legislatura=None,
                    foto_url=None,
                    email=None,
                    telefone=None,
                    situacao="Exercício",
                    esfera="estadual",
                    ente_id=ente_row["id"] if ente_row else None,
                )
            context.log.info(f"{len(govs)} governadores inseridos")

            for ibge, _nome_capital in CAPITAIS_IBGE.items():
                ente_row = await pool.fetchrow(
                    "SELECT id, uf FROM entes WHERE ibge_codigo = $1", ibge
                )
                if not ente_row:
                    continue
                prefeito = await pool.fetchrow(
                    """SELECT nome, nome_urna, cpf, partido, uf, ano_eleicao
                    FROM candidatos_tse
                    WHERE cargo ILIKE '%prefeito%'
                      AND situacao ILIKE '%eleit%'
                      AND uf = $1
                    ORDER BY ano_eleicao DESC
                    LIMIT 1""",
                    ente_row["uf"],
                )
                if prefeito:
                    await upsert_parlamentar(
                        pool,
                        id_externo=f"pref-{ibge}-{prefeito['ano_eleicao']}",
                        tipo="prefeito",
                        nome=prefeito["nome"],
                        nome_civil=prefeito["nome"],
                        cpf=prefeito["cpf"],
                        partido=prefeito["partido"],
                        uf=prefeito["uf"],
                        legislatura=None,
                        foto_url=None,
                        email=None,
                        telefone=None,
                        situacao="Exercício",
                        esfera="municipal",
                        ente_id=ente_row["id"],
                    )

            context.log.info("Prefeitos das capitais inseridos")
        finally:
            await pool.close()

    _run_async(run())

@asset(retry_policy=_API_RETRY_POLICY, group_name="votacoes", description="Votações nominais da Câmara dos Deputados + votos individuais")
def votacoes_camara(context: AssetExecutionContext):
    async def run():
        from datetime import date, timedelta

        import httpx

        from app.config import settings
        from app.queries.votacoes import upsert_orientacao, upsert_proposicao, upsert_votacao, upsert_voto
        from app.services.camara import CamaraService

        pool = await _create_pool()
        try:
            async with httpx.AsyncClient(
                base_url=settings.camara_api_url, timeout=30.0,
                headers={"Accept": "application/json"},
            ) as client:
                camara = CamaraService(client)

                hoje = date.today()
                inicio = (hoje - timedelta(days=30)).isoformat()
                fim = hoje.isoformat()

                votacoes_list = await camara.listar_todas_votacoes(inicio, fim)
                context.log.info(f"{len(votacoes_list)} votações encontradas")

                total_votos = 0
                for v in votacoes_list:

                    if v.get("siglaOrgao") != "PLEN":
                        continue

                    votacao_id_ext = str(v.get("id", ""))

                    try:
                        detail = await camara.buscar_votacao(votacao_id_ext)
                    except Exception:
                        detail = {}

                    proposicao_id = None
                    afetadas = detail.get("proposicoesAfetadas") or detail.get("objetosPossiveis") or []
                    if afetadas:
                        prop = afetadas[0]
                        prop_record = await upsert_proposicao(
                            pool,
                            id_externo=f"camara-{prop.get('id', '')}",
                            casa="camara",
                            sigla_tipo=prop.get("siglaTipo"),
                            numero=prop.get("numero"),
                            ano=prop.get("ano"),
                            ementa=prop.get("ementa"),
                            data_apresentacao=None,
                            autor=None,
                            tema=None,
                            url_inteiro_teor=None,
                        )
                        proposicao_id = prop_record["id"]

                    from datetime import datetime
                    data_hora = None
                    if v.get("dataHoraRegistro"):
                        try:
                            data_hora = datetime.fromisoformat(v["dataHoraRegistro"])
                        except (ValueError, TypeError):
                            pass

                    desc = v.get("descricao", "")
                    import re
                    sim_match = re.search(r'[Ss]im:\s*(\d+)', desc)
                    nao_match = re.search(r'[Nn]ao:\s*(\d+)', desc)
                    abs_match = re.search(r'[Aa]bsten[cç][aã]o:\s*(\d+)', desc)

                    vot_record = await upsert_votacao(
                        pool,
                        id_externo=f"camara-{votacao_id_ext}",
                        casa="camara",
                        proposicao_id=proposicao_id,
                        sigla_tipo=afetadas[0].get("siglaTipo") if afetadas else None,
                        numero=afetadas[0].get("numero") if afetadas else None,
                        ano=afetadas[0].get("ano") if afetadas else None,
                        descricao=desc,
                        data_hora=data_hora,
                        orgao="PLEN",
                        aprovada=v.get("aprovacao") == 1,
                        votos_sim=int(sim_match.group(1)) if sim_match else None,
                        votos_nao=int(nao_match.group(1)) if nao_match else None,
                        votos_abstencao=int(abs_match.group(1)) if abs_match else None,
                        votacao_secreta=False,
                    )

                    try:
                        votos_list = await camara.buscar_votos(votacao_id_ext)
                    except Exception:
                        votos_list = []

                    for voto in votos_list:
                        dep = voto.get("deputado_") or {}
                        await upsert_voto(
                            pool,
                            votacao_id=vot_record["id"],
                            parlamentar_id=None,
                            parlamentar_nome=dep.get("nome"),
                            partido=dep.get("siglaPartido"),
                            uf=dep.get("siglaUf"),
                            voto=voto.get("tipoVoto"),
                            data_registro=None,
                        )
                        total_votos += 1

                    try:
                        orientacoes = await camara.buscar_orientacoes(votacao_id_ext)
                    except Exception:
                        orientacoes = []

                    for o in orientacoes:
                        await upsert_orientacao(
                            pool,
                            votacao_id=vot_record["id"],
                            partido_bloco=o.get("siglaPartidoBloco"),
                            orientacao=o.get("orientacaoVoto"),
                        )

                context.log.info(f"Total: {total_votos} votos individuais da Câmara")
        finally:
            await pool.close()

    _run_async(run())

@asset(retry_policy=_API_RETRY_POLICY, group_name="votacoes", description="Votações nominais do Senado Federal + votos individuais")
def votacoes_senado(context: AssetExecutionContext):
    async def run():
        from datetime import datetime

        import httpx

        from app.queries.votacoes import upsert_proposicao, upsert_votacao, upsert_voto
        from app.services.senado import SenadoService

        pool = await _create_pool()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                senado = SenadoService(client)
                votacoes_list = await senado.listar_votacoes(page_size=50)
                context.log.info(f"{len(votacoes_list)} votações do Senado")

                total_votos = 0
                for v in votacoes_list:

                    proposicao_id = None
                    sigla = v.get("sigla")
                    numero = v.get("numero")
                    if sigla and numero:
                        prop_record = await upsert_proposicao(
                            pool,
                            id_externo=f"senado-{v.get('codigoMateria', '')}",
                            casa="senado",
                            sigla_tipo=sigla,
                            numero=int(numero) if str(numero).isdigit() else None,
                            ano=v.get("ano"),
                            ementa=v.get("ementa"),
                            data_apresentacao=None,
                            autor=None,
                            tema=None,
                            url_inteiro_teor=None,
                        )
                        proposicao_id = prop_record["id"]

                    data_hora = None
                    if v.get("dataSessao"):
                        try:
                            data_hora = datetime.fromisoformat(v["dataSessao"])
                        except (ValueError, TypeError):
                            pass

                    votacao_id_ext = f"senado-{v.get('codigoSessaoVotacao', '')}-{v.get('codigoSessao', '')}"
                    vot_record = await upsert_votacao(
                        pool,
                        id_externo=votacao_id_ext,
                        casa="senado",
                        proposicao_id=proposicao_id,
                        sigla_tipo=sigla,
                        numero=int(numero) if numero and str(numero).isdigit() else None,
                        ano=v.get("ano"),
                        descricao=v.get("descricaoVotacao"),
                        data_hora=data_hora,
                        orgao="PLEN",
                        aprovada=v.get("resultadoVotacao") == "A",
                        votos_sim=v.get("totalVotosSim"),
                        votos_nao=v.get("totalVotosNao"),
                        votos_abstencao=v.get("totalVotosAbstencao"),
                        votacao_secreta=v.get("votacaoSecreta") == "S",
                    )

                    for voto in (v.get("votos") or []):
                        await upsert_voto(
                            pool,
                            votacao_id=vot_record["id"],
                            parlamentar_id=None,
                            parlamentar_nome=voto.get("nomeParlamentar"),
                            partido=voto.get("siglaPartidoParlamentar"),
                            uf=voto.get("siglaUFParlamentar"),
                            voto=voto.get("siglaVotoParlamentar"),
                            data_registro=None,
                        )
                        total_votos += 1

                context.log.info(f"Total: {total_votos} votos individuais do Senado")
        finally:
            await pool.close()

    _run_async(run())

@asset(retry_policy=_API_RETRY_POLICY, group_name="backfill", description="Backfill: despesas CEAP da Câmara 2024-2025")
def backfill_despesas_camara(context: AssetExecutionContext):
    """Carrega despesas CEAP de 2024-2025. Rodar uma vez após deploy."""
    async def run():
        import httpx

        from app.config import settings
        from app.queries.despesas import upsert_despesa
        from app.queries.parlamentares import upsert_parlamentar
        from app.queries.raw_ingestao import inserir_raw
        from app.services.camara import CamaraService

        def _to_int(val, default=None):
            try: return int(val) if val not in (None, "") else default
            except (ValueError, TypeError): return default

        def _to_float(val, default=None):
            try: return float(val) if val not in (None, "") else default
            except (ValueError, TypeError): return default

        def _clean_cnpj(val):
            if not val: return None
            return str(val).replace(".", "").replace("/", "").replace("-", "").strip() or None

        pool = await _create_pool()
        try:
            async with httpx.AsyncClient(
                base_url=settings.camara_api_url, timeout=30.0,
                headers={"Accept": "application/json"},
            ) as client:
                camara = CamaraService(client)
                legislatura = await camara.buscar_legislatura_atual()
                deputados_api = await camara.listar_todos_deputados(legislatura=legislatura)

                deputados = []
                for dep in deputados_api:
                    await inserir_raw(pool, fonte="camara", tipo="deputados", payload=dep)
                    record = await upsert_parlamentar(
                        pool, id_externo=str(dep["id"]), tipo="deputado",
                        nome=dep.get("nome", ""), nome_civil=dep.get("nomeCivil"),
                        cpf=None, partido=dep.get("siglaPartido"), uf=dep.get("siglaUf"),
                        legislatura=legislatura, foto_url=dep.get("urlFoto"),
                        email=dep.get("email"), telefone=None, situacao=dep.get("situacao"),
                    )
                    deputados.append({"id": record["id"], "id_externo": dep["id"], "nome": dep["nome"]})

                total = 0
                for i, dep in enumerate(deputados, 1):
                    context.log.info(f"[{i}/{len(deputados)}] Backfill despesas {dep['nome']}")
                    for ano in ANOS_BACKFILL:
                        try:
                            despesas = await camara.buscar_todas_despesas(dep["id_externo"], ano=ano)
                        except Exception as e:
                            context.log.warning(f"Erro {dep['nome']} {ano}: {e}")
                            continue
                        for d in despesas:
                            await inserir_raw(pool, fonte="camara", tipo="despesas", payload=d)
                            id_externo = f"camara-{dep['id_externo']}-{d.get('codDocumento', '')}-{d.get('numDocumento', '')}-{ano}-{d.get('mes', '')}"
                            data_emissao = None
                            if d.get("dataDocumento"):
                                try: data_emissao = date.fromisoformat(d["dataDocumento"])
                                except (ValueError, TypeError): pass
                            await upsert_despesa(
                                pool, id_externo=id_externo, parlamentar_id=dep["id"],
                                ano=_to_int(d.get("ano"), ano), mes=_to_int(d.get("mes"), 0),
                                data_emissao=data_emissao,
                                categoria=d.get("tipoDespesa", "Não informado"),
                                subcategoria=d.get("tipoDespesa"),
                                fornecedor=d.get("nomeFornecedor"),
                                cnpj_cpf=_clean_cnpj(d.get("cnpjCpfFornecedor")),
                                documento=d.get("numDocumento"),
                                valor_documento=_to_float(d.get("valorDocumento")),
                                valor_glosa=_to_float(d.get("valorGlosa"), 0),
                                valor_liquido=_to_float(d.get("valorLiquido")),
                                url_documento=d.get("urlDocumento"),
                                lote=_to_int(d.get("codLote")),
                                ressarcimento=_to_int(d.get("numRessarcimento")),
                            )
                            total += 1
                context.log.info(f"Backfill Câmara: {total} despesas (2024-2025)")
        finally:
            await pool.close()

    _run_async(run())

@asset(retry_policy=_API_RETRY_POLICY, group_name="backfill", description="Backfill: despesas Senado 2024-2025")
def backfill_senado(context: AssetExecutionContext):
    async def run():
        import httpx

        from app.queries.despesas import upsert_despesa
        from app.queries.parlamentares import upsert_parlamentar
        from app.queries.raw_ingestao import inserir_raw
        from app.services.senado import SenadoService

        pool = await _create_pool()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                senado_svc = SenadoService(client)
                senadores = await senado_svc.listar_senadores()
                nome_para_id = {}
                for sen in senadores:
                    await inserir_raw(pool, fonte="senado", tipo="senadores", payload=sen)
                    record = await upsert_parlamentar(
                        pool, id_externo=f"senado-{sen['codigo']}", tipo="senador",
                        nome=sen.get("nome"), nome_civil=sen.get("nome_completo"),
                        cpf=None, partido=sen.get("partido"), uf=sen.get("uf"),
                        legislatura=None, foto_url=sen.get("foto_url"),
                        email=sen.get("email"), telefone=None, situacao="Exercício",
                    )
                    nome_para_id[sen["nome"].upper()] = record["id"]

                total = 0
                for ano in ANOS_BACKFILL:
                    try:
                        despesas = await senado_svc.buscar_despesas_csv(ano)
                    except Exception as e:
                        context.log.warning(f"Erro Senado {ano}: {e}")
                        continue
                    for d in despesas:
                        nome_upper = (d.get("senador") or "").upper()
                        parlamentar_id = nome_para_id.get(nome_upper)
                        if not parlamentar_id:
                            continue
                        await inserir_raw(pool, fonte="senado", tipo="despesas", payload=d)
                        data_emissao = None
                        if d.get("data"):
                            try: data_emissao = date.fromisoformat(d["data"])
                            except (ValueError, TypeError):
                                try:
                                    parts = d["data"].split("/")
                                    if len(parts) == 3:
                                        data_emissao = date(int(parts[2]), int(parts[1]), int(parts[0]))
                                except (ValueError, IndexError): pass
                        cnpj_cpf = (d.get("cnpj_cpf") or "").replace(".", "").replace("/", "").replace("-", "").strip() or None
                        id_externo = f"senado-{nome_upper}-{d.get('documento', '')}-{ano}-{d.get('mes', '')}"
                        await upsert_despesa(
                            pool, id_externo=id_externo, parlamentar_id=parlamentar_id,
                            ano=d.get("ano") or ano, mes=d.get("mes") or 0,
                            data_emissao=data_emissao,
                            categoria=d.get("tipo_despesa") or "Não informado",
                            subcategoria=None, fornecedor=d.get("fornecedor"),
                            cnpj_cpf=cnpj_cpf, documento=d.get("documento"),
                            valor_documento=d.get("valor_reembolsado"), valor_glosa=0,
                            valor_liquido=d.get("valor_reembolsado"),
                            url_documento=None, lote=None, ressarcimento=None,
                        )
                        total += 1
                context.log.info(f"Backfill Senado: {total} despesas (2024-2025)")
        finally:
            await pool.close()

    _run_async(run())

@asset(retry_policy=_API_RETRY_POLICY, group_name="backfill", description="Backfill: dados federais 2024-2025 (CPGF, despesas, contratos, licitações, viagens, emendas)")
def backfill_federal(context: AssetExecutionContext):
    async def run():

        import httpx

        from app.config import settings
        from app.queries.federal import (
            upsert_contrato,
            upsert_despesa_orcamentaria,
            upsert_emenda,
        )
        from app.services.transparencia import TransparenciaService

        pool = await _create_pool()
        try:
            async with httpx.AsyncClient(
                base_url="https://api.portaldatransparencia.gov.br/api-de-dados",
                timeout=30.0,
                headers={"chave-api-dados": settings.transparencia_api_token, "Accept": "application/json"},
            ) as client:
                service = TransparenciaService(client)

                for ano in ANOS_BACKFILL:
                    context.log.info(f"Backfill federal {ano}...")

                    total_emendas = 0
                    try:
                        records = await service.buscar_emendas(ano)
                        for r in records:
                            id_ext = f"emenda-{r.get('codigoEmenda', '')}-{ano}"
                            await upsert_emenda(
                                pool, id_externo=id_ext, ano=ano,
                                autor=r.get("nomeAutor") or r.get("autor"),
                                tipo_emenda=r.get("tipoEmenda"),
                                numero=r.get("numeroEmenda"),
                                localidade_gasto=r.get("localidadeDoGasto"),
                                funcao=r.get("funcao"), subfuncao=r.get("subfuncao"),
                                valor_empenhado=r.get("valorEmpenhado"),
                                valor_liquidado=r.get("valorLiquidado"),
                                valor_pago=r.get("valorPago"),
                            )
                            total_emendas += 1
                    except Exception as e:
                        context.log.warning(f"Erro emendas {ano}: {e}")
                    context.log.info(f"  Emendas {ano}: {total_emendas}")

                    total_desp = 0
                    for codigo_orgao, nome_orgao in ORGAOS_FEDERAIS.items():
                        try:
                            records = await service.buscar_despesas_orgao(ano, codigo_orgao)
                        except Exception as e:
                            context.log.warning(f"Erro despesas {nome_orgao} {ano}: {e}")
                            continue
                        for r in records:
                            id_ext = f"desp-fed-{r.get('codigoOrgao', '')}-{codigo_orgao}-{ano}"
                            await upsert_despesa_orcamentaria(
                                pool, id_externo=id_ext, ano=ano,
                                orgao_superior_codigo=r.get("codigoOrgaoSuperior"),
                                orgao_superior_nome=r.get("orgaoSuperior"),
                                orgao_vinculado_codigo=r.get("codigoOrgao"),
                                orgao_vinculado_nome=r.get("orgao"),
                                unidade_gestora_codigo=None, unidade_gestora_nome=None,
                                funcao=None, subfuncao=None, programa=None, acao=None,
                                categoria_economica=None, grupo_despesa=None,
                                elemento_despesa=None, modalidade_licitacao=None,
                                favorecido_nome=None, favorecido_cnpj_cpf=None,
                                valor_empenhado=r.get("empenhado"),
                                valor_liquidado=r.get("liquidado"),
                                valor_pago=r.get("pago"), valor_resto_pago=None,
                            )
                            total_desp += 1
                    context.log.info(f"  Despesas orçamentárias {ano}: {total_desp}")

                    total_contratos = 0
                    data_ini = f"01/01/{ano}"
                    data_fim_str = f"31/12/{ano}"
                    for codigo_orgao, nome_orgao in ORGAOS_FEDERAIS.items():
                        try:
                            records = await service.buscar_contratos(codigo_orgao, data_ini, data_fim_str)
                        except Exception as e:
                            context.log.warning(f"Erro contratos {nome_orgao} {ano}: {e}")
                            continue
                        for r in records:
                            fornecedor = r.get("fornecedor") or {}
                            await upsert_contrato(
                                pool, id_externo=f"contrato-{r.get('id', '')}-{codigo_orgao}",
                                orgao_codigo=codigo_orgao, orgao_nome=nome_orgao,
                                unidade_gestora_codigo=str(r.get("unidadeGestora", {}).get("codigo", "")),
                                unidade_gestora_nome=r.get("unidadeGestora", {}).get("nome"),
                                fornecedor_nome=fornecedor.get("nome") or fornecedor.get("razaoSocialReceita"),
                                fornecedor_cnpj_cpf=fornecedor.get("cnpjFormatado") or fornecedor.get("cpfFormatado"),
                                objeto=r.get("objeto"), numero=r.get("numero"),
                                modalidade_licitacao=r.get("modalidadeCompra"),
                                situacao=r.get("situacaoContrato"),
                                valor_inicial=r.get("valorInicial"), valor_final=r.get("valorFinal"),
                                valor_acumulado=r.get("valorAcumulado"),
                                data_inicio=r.get("dataInicioVigencia"), data_fim=r.get("dataFimVigencia"),
                                data_publicacao=r.get("dataPublicacaoDOU"),
                            )
                            total_contratos += 1
                    context.log.info(f"  Contratos {ano}: {total_contratos}")

                context.log.info("Backfill federal concluído")
        finally:
            await pool.close()

    _run_async(run())

@asset(retry_policy=_API_RETRY_POLICY, group_name="backfill", description="Backfill: votações Câmara 2024-2025")
def backfill_votacoes_camara(context: AssetExecutionContext):
    async def run():
        import re
        from datetime import datetime

        import httpx

        from app.config import settings
        from app.queries.votacoes import upsert_orientacao, upsert_proposicao, upsert_votacao, upsert_voto
        from app.services.camara import CamaraService

        pool = await _create_pool()
        try:
            async with httpx.AsyncClient(
                base_url=settings.camara_api_url, timeout=30.0,
                headers={"Accept": "application/json"},
            ) as client:
                camara = CamaraService(client)
                total_votos = 0

                trimestres = [("01-01", "03-31"), ("04-01", "06-30"), ("07-01", "09-30"), ("10-01", "12-31")]
                for ano in ANOS_BACKFILL:
                    votacoes_list = []
                    for inicio, fim in trimestres:
                        try:
                            lote = await camara.listar_todas_votacoes(f"{ano}-{inicio}", f"{ano}-{fim}")
                            votacoes_list.extend(lote)
                            context.log.info(f"Câmara {ano} ({inicio} a {fim}): {len(lote)} votações")
                        except Exception as e:
                            context.log.warning(f"Erro Câmara {ano} ({inicio} a {fim}): {e}")
                    context.log.info(f"Câmara {ano}: {len(votacoes_list)} votações total")

                    for v in votacoes_list:
                        if v.get("siglaOrgao") != "PLEN":
                            continue

                        votacao_id_ext = str(v.get("id", ""))
                        try: detail = await camara.buscar_votacao(votacao_id_ext)
                        except Exception: detail = {}

                        proposicao_id = None
                        afetadas = detail.get("proposicoesAfetadas") or detail.get("objetosPossiveis") or []
                        if afetadas:
                            prop = afetadas[0]
                            prop_record = await upsert_proposicao(
                                pool, id_externo=f"camara-{prop.get('id', '')}",
                                casa="camara", sigla_tipo=prop.get("siglaTipo"),
                                numero=prop.get("numero"), ano=prop.get("ano"),
                                ementa=prop.get("ementa"), data_apresentacao=None,
                                autor=None, tema=None, url_inteiro_teor=None,
                            )
                            proposicao_id = prop_record["id"]

                        data_hora = None
                        if v.get("dataHoraRegistro"):
                            try: data_hora = datetime.fromisoformat(v["dataHoraRegistro"])
                            except (ValueError, TypeError): pass

                        desc = v.get("descricao", "")
                        sim_match = re.search(r'[Ss]im:\s*(\d+)', desc)
                        nao_match = re.search(r'[Nn]ao:\s*(\d+)', desc)
                        abs_match = re.search(r'[Aa]bsten[cç][aã]o:\s*(\d+)', desc)

                        vot_record = await upsert_votacao(
                            pool, id_externo=f"camara-{votacao_id_ext}", casa="camara",
                            proposicao_id=proposicao_id,
                            sigla_tipo=afetadas[0].get("siglaTipo") if afetadas else None,
                            numero=afetadas[0].get("numero") if afetadas else None,
                            ano=afetadas[0].get("ano") if afetadas else None,
                            descricao=desc, data_hora=data_hora, orgao="PLEN",
                            aprovada=v.get("aprovacao") == 1,
                            votos_sim=int(sim_match.group(1)) if sim_match else None,
                            votos_nao=int(nao_match.group(1)) if nao_match else None,
                            votos_abstencao=int(abs_match.group(1)) if abs_match else None,
                            votacao_secreta=False,
                        )

                        try: votos_list = await camara.buscar_votos(votacao_id_ext)
                        except Exception: votos_list = []
                        for voto in votos_list:
                            dep = voto.get("deputado_") or {}
                            await upsert_voto(
                                pool, votacao_id=vot_record["id"], parlamentar_id=None,
                                parlamentar_nome=dep.get("nome"), partido=dep.get("siglaPartido"),
                                uf=dep.get("siglaUf"), voto=voto.get("tipoVoto"), data_registro=None,
                            )
                            total_votos += 1

                        try: orientacoes = await camara.buscar_orientacoes(votacao_id_ext)
                        except Exception: orientacoes = []
                        for o in orientacoes:
                            await upsert_orientacao(
                                pool, votacao_id=vot_record["id"],
                                partido_bloco=o.get("siglaPartidoBloco"),
                                orientacao=o.get("orientacaoVoto"),
                            )

                context.log.info(f"Backfill votações Câmara: {total_votos} votos (2024-2025)")
        finally:
            await pool.close()

    _run_async(run())

@asset(retry_policy=_API_RETRY_POLICY, group_name="backfill", description="Backfill: dados fiscais SICONFI 2024-2025 (estados + capitais)")
def backfill_fiscal(context: AssetExecutionContext):
    async def run():
        from app.queries.entes import buscar_ente_por_ibge
        from app.queries.federal import upsert_dado_fiscal
        from app.services.siconfi import SiconfiService

        pool = await _create_pool()
        try:
            service = SiconfiService()
            total = 0

            for ano in ANOS_BACKFILL:

                for ibge, _uf in ESTADOS_IBGE.items():
                    ente = await buscar_ente_por_ibge(pool, ibge)
                    if not ente: continue
                    for periodo in range(1, 7):
                        try:
                            for r in await service.buscar_rreo(ibge, ano, periodo):
                                await upsert_dado_fiscal(pool, ente_id=ente["id"], exercicio=r.get("exercicio", ano), periodo=r.get("periodo", periodo), demonstrativo="RREO", anexo=r.get("anexo", ""), coluna=r.get("coluna"), rotulo=r.get("rotulo"), valor=r.get("valor"))
                                total += 1
                        except Exception: pass
                    for periodo in range(1, 4):
                        try:
                            for r in await service.buscar_rgf(ibge, ano, periodo):
                                await upsert_dado_fiscal(pool, ente_id=ente["id"], exercicio=r.get("exercicio", ano), periodo=r.get("periodo", periodo), demonstrativo="RGF", anexo=r.get("anexo", ""), coluna=r.get("coluna"), rotulo=r.get("rotulo"), valor=r.get("valor"))
                                total += 1
                        except Exception: pass

                for ibge, _nome in CAPITAIS_IBGE.items():
                    ente = await buscar_ente_por_ibge(pool, ibge)
                    if not ente: continue
                    for periodo in range(1, 7):
                        try:
                            for r in await service.buscar_rreo(ibge, ano, periodo):
                                await upsert_dado_fiscal(pool, ente_id=ente["id"], exercicio=r.get("exercicio", ano), periodo=r.get("periodo", periodo), demonstrativo="RREO", anexo=r.get("anexo", ""), coluna=r.get("coluna"), rotulo=r.get("rotulo"), valor=r.get("valor"))
                                total += 1
                        except Exception: pass
                    for periodo in range(1, 4):
                        try:
                            for r in await service.buscar_rgf(ibge, ano, periodo, esfera="E"):
                                await upsert_dado_fiscal(pool, ente_id=ente["id"], exercicio=r.get("exercicio", ano), periodo=r.get("periodo", periodo), demonstrativo="RGF", anexo=r.get("anexo", ""), coluna=r.get("coluna"), rotulo=r.get("rotulo"), valor=r.get("valor"))
                                total += 1
                        except Exception: pass

                context.log.info(f"Backfill fiscal {ano}: {total} registros acumulados")

            await service.close()
            context.log.info(f"Backfill fiscal total: {total}")
        finally:
            await pool.close()

    _run_async(run())

@asset(retry_policy=_API_RETRY_POLICY, group_name="backfill", description="Backfill: votações Senado 2024-2025")
def backfill_votacoes_senado(context: AssetExecutionContext):
    async def run():
        from datetime import datetime

        import httpx

        from app.queries.votacoes import upsert_proposicao, upsert_votacao, upsert_voto
        from app.services.senado import SenadoService

        pool = await _create_pool()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                senado = SenadoService(client)
                total_votos = 0

                for ano in ANOS_BACKFILL:
                    votacoes_list = await senado.listar_votacoes(page_size=1000, ano=ano)
                    context.log.info(f"Senado {ano}: {len(votacoes_list)} votações")

                    for v in votacoes_list:
                        proposicao_id = None
                        sigla = v.get("sigla")
                        numero = v.get("numero")
                        if sigla and numero:
                            prop_record = await upsert_proposicao(
                                pool,
                                id_externo=f"senado-{v.get('codigoMateria', '')}",
                                casa="senado",
                                sigla_tipo=sigla,
                                numero=int(numero) if str(numero).isdigit() else None,
                                ano=v.get("ano"),
                                ementa=v.get("ementa"),
                                data_apresentacao=None,
                                autor=None,
                                tema=None,
                                url_inteiro_teor=None,
                            )
                            proposicao_id = prop_record["id"]

                        data_hora = None
                        if v.get("dataSessao"):
                            try:
                                data_hora = datetime.fromisoformat(v["dataSessao"])
                            except (ValueError, TypeError):
                                pass

                        votacao_id_ext = f"senado-{v.get('codigoSessaoVotacao', '')}-{v.get('codigoSessao', '')}"
                        vot_record = await upsert_votacao(
                            pool,
                            id_externo=votacao_id_ext,
                            casa="senado",
                            proposicao_id=proposicao_id,
                            sigla_tipo=sigla,
                            numero=int(numero) if numero and str(numero).isdigit() else None,
                            ano=v.get("ano"),
                            descricao=v.get("descricaoVotacao"),
                            data_hora=data_hora,
                            orgao="PLEN",
                            aprovada=v.get("resultadoVotacao") == "A",
                            votos_sim=v.get("totalVotosSim"),
                            votos_nao=v.get("totalVotosNao"),
                            votos_abstencao=v.get("totalVotosAbstencao"),
                            votacao_secreta=v.get("votacaoSecreta") == "S",
                        )

                        for voto in (v.get("votos") or []):
                            await upsert_voto(
                                pool,
                                votacao_id=vot_record["id"],
                                parlamentar_id=None,
                                parlamentar_nome=voto.get("nomeParlamentar"),
                                partido=voto.get("siglaPartidoParlamentar"),
                                uf=voto.get("siglaUFParlamentar"),
                                voto=voto.get("siglaVotoParlamentar"),
                                data_registro=None,
                            )
                            total_votos += 1

                context.log.info(f"Backfill votações Senado: {total_votos} votos (2024-2025)")
        finally:
            await pool.close()

    _run_async(run())

carga_fase1_backfill = define_asset_job(
    "carga_fase1_backfill",
    selection=[
        backfill_despesas_camara, backfill_senado,
        backfill_federal, backfill_votacoes_camara, backfill_votacoes_senado,
        backfill_fiscal,
    ],
    description="Fase 1: Backfill historico 2024-2025 (disparar manualmente)",
)

carga_fase2_enriquecimento = define_asset_job(
    "carga_fase2_enriquecimento",
    selection=[empresas_cnpj, sancoes, candidatos_tse, governadores_prefeitos],
    description="Fase 2: Enriquecimento (disparado apos Fase 1)",
)

carga_fase3_correntes = define_asset_job(
    "carga_fase3_correntes",
    selection=[
        parlamentares_camara, despesas_camara, senado,
        cpgf_federal, despesas_federais, contratos_federais,
        licitacoes_federais, viagens_federais, emendas_parlamentares,
        votacoes_camara, votacoes_senado,
        fiscal_estados, fiscal_capitais,
    ],
    description="Fase 3: Dados correntes 2026 (disparado apos Fase 2)",
)

carga_fase4_analise = define_asset_job(
    "carga_fase4_analise",
    selection=[suspeitas, analise_recibos, embeddings, feed_eventos_dagster],
    description="Fase 4: Analise e alertas (disparado apos Fase 3)",
)

@run_status_sensor(
    run_status=DagsterRunStatus.SUCCESS,
    monitored_jobs=[carga_fase1_backfill],
    request_job=carga_fase2_enriquecimento,
    name="sensor_fase1_para_fase2",
    description="Dispara Fase 2 quando Fase 1 completa com sucesso. Ativar manualmente antes de rodar carga inicial.",
    default_status=DefaultSensorStatus.STOPPED,
)
def sensor_fase1_para_fase2(context):
    return RunRequest()

@run_status_sensor(
    run_status=DagsterRunStatus.SUCCESS,
    monitored_jobs=[carga_fase2_enriquecimento],
    request_job=carga_fase3_correntes,
    name="sensor_fase2_para_fase3",
    description="Dispara Fase 3 quando Fase 2 completa com sucesso. Ativar manualmente antes de rodar carga inicial.",
    default_status=DefaultSensorStatus.STOPPED,
)
def sensor_fase2_para_fase3(context):
    return RunRequest()

@run_status_sensor(
    run_status=DagsterRunStatus.SUCCESS,
    monitored_jobs=[carga_fase3_correntes],
    request_job=carga_fase4_analise,
    name="sensor_fase3_para_fase4",
    description="Dispara Fase 4 quando Fase 3 completa com sucesso. Ativar manualmente antes de rodar carga inicial.",
    default_status=DefaultSensorStatus.STOPPED,
)
def sensor_fase3_para_fase4(context):
    return RunRequest()

ingestao_diaria = define_asset_job(
    "ingestao_diaria",
    selection=[parlamentares_camara, despesas_camara, senado, suspeitas],
)

ingestao_federal_diaria = define_asset_job(
    "ingestao_federal_diaria",
    selection=[cpgf_federal, despesas_federais, viagens_federais, votacoes_camara, votacoes_senado],
)

ingestao_semanal = define_asset_job(
    "ingestao_semanal",
    selection=[
        sancoes, contratos_federais, licitacoes_federais,
        emendas_parlamentares, analise_recibos, feed_eventos_dagster,
    ],
)

embeddings_diario = define_asset_job(
    "embeddings_diario",
    selection=[embeddings],
    description="Gera embeddings para registros novos (roda após ingestões diárias)",
    tags={"dagster/max_concurrent_runs": "1"},
)

ingestao_fiscal_semanal = define_asset_job(
    "ingestao_fiscal_semanal",
    selection=[fiscal_estados, fiscal_capitais],
)

ingestao_mensal = define_asset_job(
    "ingestao_mensal",
    selection=[empresas_cnpj, candidatos_tse, governadores_prefeitos],
)

schedule_diario = ScheduleDefinition(
    job=ingestao_diaria,
    cron_schedule="0 3 * * *",
)

schedule_federal_diario = ScheduleDefinition(
    job=ingestao_federal_diaria,
    cron_schedule="0 4 * * *",
)

schedule_semanal = ScheduleDefinition(
    job=ingestao_semanal,
    cron_schedule="0 2 * * 0",
)

@run_status_sensor(
    run_status=DagsterRunStatus.SUCCESS,
    monitored_jobs=[
        ingestao_diaria, ingestao_federal_diaria,
        ingestao_semanal, ingestao_fiscal_semanal,
        ingestao_mensal,
    ],
    request_job=embeddings_diario,
    name="sensor_embeddings_apos_ingestao",
    description="Dispara embeddings imediatamente apos qualquer ingestao completar com sucesso",
    default_status=DefaultSensorStatus.RUNNING,
)
def sensor_embeddings_apos_ingestao(context):
    return RunRequest()

schedule_fiscal_semanal = ScheduleDefinition(
    job=ingestao_fiscal_semanal,
    cron_schedule="0 5 * * 0",
)

schedule_mensal = ScheduleDefinition(
    job=ingestao_mensal,
    cron_schedule="0 1 1 * *",
)

defs = Definitions(
    assets=[

        parlamentares_camara, despesas_camara, senado,

        cpgf_federal, despesas_federais, contratos_federais,
        licitacoes_federais, viagens_federais, emendas_parlamentares,

        fiscal_estados, fiscal_capitais,

        votacoes_camara, votacoes_senado,

        governadores_prefeitos,

        empresas_cnpj, sancoes, candidatos_tse,

        suspeitas, analise_recibos, embeddings, embeddings_glossario,

        feed_eventos_dagster,

        backfill_despesas_camara, backfill_senado,
        backfill_federal, backfill_votacoes_camara, backfill_votacoes_senado,
        backfill_fiscal,
    ],
    jobs=[

        ingestao_diaria, ingestao_federal_diaria,
        ingestao_semanal, ingestao_fiscal_semanal,
        ingestao_mensal, embeddings_diario,

        carga_fase1_backfill,
        carga_fase2_enriquecimento,
        carga_fase3_correntes,
        carga_fase4_analise,
    ],
    schedules=[
        schedule_diario, schedule_federal_diario,
        schedule_semanal, schedule_fiscal_semanal,
        schedule_mensal,
    ],
    sensors=[
        sensor_fase1_para_fase2,
        sensor_fase2_para_fase3,
        sensor_fase3_para_fase4,
        sensor_embeddings_apos_ingestao,
    ],
)
