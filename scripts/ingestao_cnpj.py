"""
Ingestão bulk de CNPJ da Receita Federal.

Downloads CSVs de arquivos.receitafederal.gov.br, parseia e insere na tabela empresas.
Os arquivos são: Empresas (10 partes) + Estabelecimentos (10 partes).

Layout: https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf
Formato: CSV sem header, separador ;, encoding latin-1, campos entre aspas

Uso:
    python scripts/ingestao_cnpj.py                    # download + ingestão completa
    python scripts/ingestao_cnpj.py --skip-download     # só ingestão (arquivos já baixados)
    python scripts/ingestao_cnpj.py --only-despesas     # só CNPJs que aparecem nas despesas
"""

import argparse
import asyncio
import csv
import io
import logging
import os
import sys
import zipfile
from pathlib import Path

import httpx

sys.path.insert(0, "/app")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "terreiro"))

import asyncpg

from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj"
DATA_DIR = Path("/tmp/cnpj_data")

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

async def download_files(client: httpx.AsyncClient, only_despesas_cnpjs: set[str] | None = None):
    """Baixa os ZIPs de Empresas e Estabelecimentos da Receita Federal."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Buscando lista de arquivos da Receita Federal...")
    try:
        resp = await client.get(f"{BASE_URL}/2025-03/")
        resp.raise_for_status()

        import re
        links = re.findall(r'href="([^"]*\.zip)"', resp.text, re.IGNORECASE)
        if not links:

            resp = await client.get(f"{BASE_URL}/")
            links = re.findall(r'href="([^"]*\.zip)"', resp.text, re.IGNORECASE)
    except Exception as e:
        logger.warning(f"Erro listando arquivos: {e}. Usando nomes padrão.")
        links = []

    if not links:
        links = [f"Empresas{i}.zip" for i in range(10)] + [f"Estabelecimentos{i}.zip" for i in range(10)]

    for filename in links:
        if not (filename.startswith("Empresa") or filename.startswith("Estabelecimento")):
            continue

        filepath = DATA_DIR / filename
        if filepath.exists():
            logger.info(f"  {filename} já existe, pulando")
            continue

        url = f"{BASE_URL}/2025-03/{filename}" if "2025-03" not in filename else f"{BASE_URL}/{filename}"
        logger.info(f"  Baixando {filename}...")
        try:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                with open(filepath, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=1024 * 1024):
                        f.write(chunk)
            logger.info(f"  {filename} OK ({filepath.stat().st_size / 1024 / 1024:.0f} MB)")
        except Exception as e:
            logger.warning(f"  Erro baixando {filename}: {e}")

def parse_csv_from_zip(zip_path: Path, fields: list[str]) -> list[dict]:
    """Extrai e parseia CSV de dentro do ZIP."""
    rows = []
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if not name.endswith(".csv") and not name.endswith(".CSV"):

                pass
            with zf.open(name) as f:
                text = f.read().decode("latin-1")
                reader = csv.reader(io.StringIO(text), delimiter=";", quotechar='"')
                for line in reader:
                    if len(line) >= len(fields):
                        row = {fields[i]: line[i].strip().strip('"') for i in range(len(fields))}
                        rows.append(row)
    return rows

def parse_date(val: str) -> str | None:
    """Converte data no formato YYYYMMDD para YYYY-MM-DD."""
    val = val.strip()
    if not val or val == "0" or len(val) != 8:
        return None
    try:
        return f"{val[:4]}-{val[4:6]}-{val[6:8]}"
    except (ValueError, IndexError):
        return None

def parse_decimal(val: str) -> float | None:
    val = val.strip().replace(",", ".")
    if not val:
        return None
    try:
        return float(val)
    except ValueError:
        return None

async def ingest_empresas(pool: asyncpg.Pool, cnpjs_filter: set[str] | None = None):
    """Processa arquivos de Empresas."""
    total = 0
    for zip_path in sorted(DATA_DIR.glob("Empresa*.zip")):
        logger.info(f"Processando {zip_path.name}...")
        rows = parse_csv_from_zip(zip_path, EMPRESAS_FIELDS)

        batch = []
        for row in rows:
            cnpj_basico = row["cnpj_basico"]
            if cnpjs_filter and cnpj_basico not in cnpjs_filter:
                continue

            batch.append((
                cnpj_basico,
                row.get("razao_social") or None,
                row.get("natureza_juridica") or None,
                row.get("qualificacao_responsavel") or None,
                parse_decimal(row.get("capital_social", "")),
                row.get("porte") or None,
                row.get("ente_federativo") or None,
            ))

            if len(batch) >= 5000:
                await _batch_upsert_empresas(pool, batch)
                total += len(batch)
                batch = []

        if batch:
            await _batch_upsert_empresas(pool, batch)
            total += len(batch)

        logger.info(f"  {zip_path.name}: {total} empresas acumuladas")

    logger.info(f"Total empresas processadas: {total}")
    return total

async def _batch_upsert_empresas(pool: asyncpg.Pool, batch: list[tuple]):
    """Upsert em batch para empresas (dados da tabela EMPRESAS da Receita)."""
    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO empresas (cnpj, cnpj_basico, razao_social, natureza_juridica,
                                  qualificacao_responsavel, capital_social, porte, ente_federativo, fonte)
            VALUES ($1, $1, $2, $3, $4, $5, $6, $7, 'bulk')
            ON CONFLICT (cnpj) DO UPDATE SET
                razao_social = COALESCE(EXCLUDED.razao_social, empresas.razao_social),
                natureza_juridica = COALESCE(EXCLUDED.natureza_juridica, empresas.natureza_juridica),
                capital_social = COALESCE(EXCLUDED.capital_social, empresas.capital_social),
                porte = COALESCE(EXCLUDED.porte, empresas.porte),
                updated_at = NOW()
            """,
            [(r[0], r[1], r[2], r[3], r[4], r[5], r[6]) for r in batch],
        )

async def ingest_estabelecimentos(pool: asyncpg.Pool, cnpjs_filter: set[str] | None = None):
    """Processa arquivos de Estabelecimentos."""
    total = 0
    for zip_path in sorted(DATA_DIR.glob("Estabelecimento*.zip")):
        logger.info(f"Processando {zip_path.name}...")
        rows = parse_csv_from_zip(zip_path, ESTABELECIMENTOS_FIELDS)

        batch = []
        for row in rows:
            cnpj_basico = row["cnpj_basico"]
            if cnpjs_filter and cnpj_basico not in cnpjs_filter:
                continue

            cnpj_full = f"{cnpj_basico}{row.get('cnpj_ordem', '0001')}{row.get('cnpj_dv', '00')}"
            sit_code = row.get("situacao_cadastral", "")
            situacao = SITUACAO_MAP.get(sit_code.zfill(2), sit_code)

            batch.append((
                cnpj_full,
                cnpj_basico,
                row.get("cnpj_ordem") or None,
                row.get("cnpj_dv") or None,
                row.get("matriz_filial") or None,
                row.get("nome_fantasia") or None,
                situacao,
                parse_date(row.get("data_situacao", "")),
                row.get("motivo_situacao") or None,
                parse_date(row.get("data_inicio", "")),
                row.get("cnae_principal") or None,
                row.get("cnae_secundaria") or None,
                row.get("tipo_logradouro") or None,
                row.get("logradouro") or None,
                row.get("numero") or None,
                row.get("complemento") or None,
                row.get("bairro") or None,
                row.get("cep") or None,
                row.get("uf") or None,
                row.get("municipio") or None,
                row.get("ddd1") or None,
                row.get("telefone1") or None,
                row.get("email") or None,
            ))

            if len(batch) >= 5000:
                await _batch_upsert_estabelecimentos(pool, batch)
                total += len(batch)
                batch = []

        if batch:
            await _batch_upsert_estabelecimentos(pool, batch)
            total += len(batch)

        logger.info(f"  {zip_path.name}: {total} estabelecimentos acumulados")

    logger.info(f"Total estabelecimentos processados: {total}")
    return total

async def _batch_upsert_estabelecimentos(pool: asyncpg.Pool, batch: list[tuple]):
    """Upsert em batch para estabelecimentos."""
    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO empresas (cnpj, cnpj_basico, cnpj_ordem, cnpj_dv, matriz_filial,
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
                updated_at = NOW()
            """,
            batch,
        )

async def get_cnpjs_from_despesas(pool: asyncpg.Pool) -> set[str]:
    """Retorna o set de CNPJ básicos (8 primeiros dígitos) presentes nas despesas."""
    rows = await pool.fetch(
        "SELECT DISTINCT LEFT(cnpj_cpf, 8) AS cnpj_basico FROM despesas WHERE cnpj_cpf IS NOT NULL AND LENGTH(cnpj_cpf) >= 8"
    )
    return {r["cnpj_basico"] for r in rows}

async def main():
    parser = argparse.ArgumentParser(description="Ingestão bulk de CNPJ da Receita Federal")
    parser.add_argument("--skip-download", action="store_true", help="Pular download (usar arquivos já baixados)")
    parser.add_argument("--only-despesas", action="store_true", help="Só CNPJs que aparecem nas despesas")
    args = parser.parse_args()

    pool = await asyncpg.create_pool(dsn=settings.database_url, min_size=2, max_size=10)

    try:
        cnpjs_filter = None
        if args.only_despesas:
            cnpjs_filter = await get_cnpjs_from_despesas(pool)
            logger.info(f"Filtrando por {len(cnpjs_filter)} CNPJs das despesas")

        if not args.skip_download:
            async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
                await download_files(client, cnpjs_filter)

        await ingest_empresas(pool, cnpjs_filter)
        await ingest_estabelecimentos(pool, cnpjs_filter)

    finally:
        await pool.close()

    logger.info("Ingestão CNPJ concluída!")

if __name__ == "__main__":
    asyncio.run(main())
