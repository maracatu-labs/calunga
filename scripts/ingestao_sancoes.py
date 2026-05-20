"""
Ingestão de sanções (CEIS/CNEP/CEPIM) do Portal da Transparência.

Uso:
    python scripts/ingestao_sancoes.py
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, "/app")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "terreiro"))

import asyncpg
import httpx

from app.config import settings
from app.services.transparencia import TransparenciaService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def _extract_cnpj(record: dict) -> str | None:
    """Extrai CNPJ/CPF do registro de sanção (formato varia por endpoint)."""
    for key in ["cpfCnpjSancionado", "cnpjSancionado", "cnpjEntidade", "cpfCnpj"]:
        val = record.get(key, "")
        if val:
            return val.replace(".", "").replace("/", "").replace("-", "").strip()

    pessoa = record.get("pessoaSancionada") or record.get("sancionado") or {}
    for key in ["cpfCnpj", "cnpjCpf", "numeroInscricaoSocial"]:
        val = pessoa.get(key, "")
        if val:
            return val.replace(".", "").replace("/", "").replace("-", "").strip()
    return None

def _extract_nome(record: dict) -> str | None:
    for key in ["nomeSancionado", "nomeEntidade", "razaoSocialReceita"]:
        val = record.get(key)
        if val:
            return val.strip()
    pessoa = record.get("pessoaSancionada") or record.get("sancionado") or {}
    return pessoa.get("nome") or pessoa.get("razaoSocialReceita")

def _extract_orgao(record: dict) -> str | None:
    orgao = record.get("orgaoSancionador") or {}
    if isinstance(orgao, dict):
        return orgao.get("nome") or orgao.get("siglaUf")
    return str(orgao) if orgao else None

def _extract_date(record: dict, key: str) -> str | None:
    val = record.get(key, "")
    if not val:
        return None

    if "/" in val:
        parts = val.split("/")
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    return val[:10] if len(val) >= 10 else None

async def ingest_sancoes(pool: asyncpg.Pool, tipo: str, records: list[dict]) -> int:
    """Insere registros de sanção na tabela."""
    total = 0
    for record in records:
        cpf_cnpj = _extract_cnpj(record)
        if not cpf_cnpj:
            continue

        nome = _extract_nome(record)
        orgao = _extract_orgao(record)
        data_inicio = _extract_date(record, "dataInicioSancao") or _extract_date(record, "dataPublicacao")
        data_fim = _extract_date(record, "dataFimSancao") or _extract_date(record, "dataFinalSancao")
        fundamentacao = record.get("fundamentacaoLegal") or record.get("textoFundamentacao")

        try:
            await pool.execute(
                """
                INSERT INTO sancoes (tipo, cpf_cnpj, nome, orgao_sancionador, fundamentacao_legal, data_inicio, data_fim)
                VALUES ($1, $2, $3, $4, $5, $6::date, $7::date)
                ON CONFLICT DO NOTHING
                """,
                tipo,
                cpf_cnpj,
                nome,
                orgao,
                fundamentacao,
                data_inicio,
                data_fim,
            )
            total += 1
        except Exception as e:
            logger.warning(f"Erro inserindo sanção {cpf_cnpj}: {e}")

    return total

async def main():
    pool = await asyncpg.create_pool(dsn=settings.database_url, min_size=2, max_size=5)

    try:
        async with httpx.AsyncClient(
            base_url="https://api.portaldatransparencia.gov.br/api-de-dados",
            timeout=30.0,
            headers={
                "chave-api-dados": settings.transparencia_api_token,
                "Accept": "application/json",
            },
        ) as client:
            service = TransparenciaService(client)

            for tipo, fetcher in [("CEIS", service.buscar_ceis), ("CNEP", service.buscar_cnep), ("CEPIM", service.buscar_cepim)]:
                try:
                    records = await fetcher()
                    total = await ingest_sancoes(pool, tipo, records)
                    logger.info(f"{tipo}: {total} sanções inseridas de {len(records)} registros")
                except Exception as e:
                    logger.warning(f"Erro ingerindo {tipo}: {e}")

    finally:
        await pool.close()

    logger.info("Ingestão de sanções concluída!")

if __name__ == "__main__":
    asyncio.run(main())
