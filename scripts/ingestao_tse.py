"""
Ingestão de dados do TSE (candidatos e prestação de contas).

Fonte: https://dadosabertos.tse.jus.br/
Download: CSVs de consulta de candidatos

Uso:
    python scripts/ingestao_tse.py --ano 2022
    python scripts/ingestao_tse.py --ano 2024
"""

import argparse
import asyncio
import csv
import io
import logging
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

DATA_DIR = Path("/tmp/tse_data")
TSE_URL = "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_{ano}.zip"

async def download_candidatos(client: httpx.AsyncClient, ano: int) -> Path:
    """Baixa o ZIP de candidatos do TSE."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = DATA_DIR / f"consulta_cand_{ano}.zip"

    if filepath.exists():
        logger.info(f"Arquivo {filepath.name} já existe")
        return filepath

    url = TSE_URL.format(ano=ano)
    logger.info(f"Baixando {url}...")
    async with client.stream("GET", url) as resp:
        resp.raise_for_status()
        with open(filepath, "wb") as f:
            async for chunk in resp.aiter_bytes(chunk_size=1024 * 1024):
                f.write(chunk)

    logger.info(f"Download OK ({filepath.stat().st_size / 1024 / 1024:.0f} MB)")
    return filepath

def parse_candidatos_csv(zip_path: Path) -> list[dict]:
    """Extrai candidatos do ZIP do TSE."""
    candidatos = []

    with zipfile.ZipFile(zip_path) as zf:
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
                    candidatos.append({
                        "ano_eleicao": _int(row.get("ANO_ELEICAO") or row.get("DT_ELEICAO", "")[:4]),
                        "tipo_eleicao": row.get("DS_ELEICAO", "").strip(),
                        "uf": row.get("SG_UF", "").strip(),
                        "cargo": row.get("DS_CARGO", "").strip(),
                        "numero_candidato": row.get("NR_CANDIDATO", "").strip(),
                        "nome": row.get("NM_CANDIDATO", "").strip(),
                        "nome_urna": row.get("NM_URNA_CANDIDATO", "").strip(),
                        "cpf": _clean_doc(row.get("NR_CPF_CANDIDATO", "")),
                        "cnpj_campanha": _clean_doc(row.get("NR_CNPJ_PRESTADOR_CONTA", "")),
                        "partido": row.get("SG_PARTIDO", "").strip(),
                        "situacao": row.get("DS_SIT_TOT_TURNO", "").strip() or row.get("DS_SITUACAO_CANDIDATURA", "").strip(),
                    })

    return candidatos

async def ingest_candidatos(pool: asyncpg.Pool, candidatos: list[dict]) -> int:
    total = 0
    batch = []

    for c in candidatos:
        if not c.get("nome"):
            continue

        batch.append((
            c.get("ano_eleicao"),
            c.get("tipo_eleicao"),
            c.get("uf"),
            c.get("cargo"),
            c.get("numero_candidato"),
            c.get("nome"),
            c.get("nome_urna"),
            c.get("cpf"),
            c.get("cnpj_campanha"),
            c.get("partido"),
            c.get("situacao"),
        ))

        if len(batch) >= 5000:
            await _batch_insert(pool, batch)
            total += len(batch)
            batch = []

    if batch:
        await _batch_insert(pool, batch)
        total += len(batch)

    return total

async def _batch_insert(pool: asyncpg.Pool, batch: list[tuple]):
    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO candidatos_tse (ano_eleicao, tipo_eleicao, uf, cargo, numero_candidato,
                                        nome, nome_urna, cpf, cnpj_campanha, partido, situacao)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            """,
            batch,
        )

def _int(val) -> int | None:
    try:
        return int(str(val).strip())
    except (ValueError, TypeError):
        return None

def _clean_doc(val: str) -> str | None:
    v = val.replace(".", "").replace("/", "").replace("-", "").strip()
    return v if v and v != "0" else None

async def main():
    parser = argparse.ArgumentParser(description="Ingestão de candidatos do TSE")
    parser.add_argument("--ano", type=int, required=True, help="Ano da eleição (ex: 2022, 2024)")
    args = parser.parse_args()

    pool = await asyncpg.create_pool(dsn=settings.database_url, min_size=2, max_size=5)

    try:
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            zip_path = await download_candidatos(client, args.ano)

        candidatos = parse_candidatos_csv(zip_path)
        logger.info(f"Parseados {len(candidatos)} candidatos")

        total = await ingest_candidatos(pool, candidatos)
        logger.info(f"Inseridos {total} candidatos")

    finally:
        await pool.close()

    logger.info("Ingestão TSE concluída!")

if __name__ == "__main__":
    asyncio.run(main())
