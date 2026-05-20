"""
Seed script: popular banco com senadores + despesas reais do Senado Federal.

Uso:
    python scripts/seed_senado.py                  # anos 2024-2025
    python scripts/seed_senado.py --ano 2025       # só 2025
"""

import argparse
import asyncio
import logging
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, "/app")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "terreiro"))

import asyncpg
import httpx

from app.config import settings
from app.queries.parlamentares import upsert_parlamentar
from app.queries.despesas import upsert_despesa
from app.queries.raw_ingestao import inserir_raw
from app.services.senado import SenadoService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

async def seed_senadores(pool: asyncpg.Pool, senado: SenadoService) -> dict[str, int]:
    """Busca senadores em exercício e insere no banco. Retorna mapa nome→id."""
    senadores = await senado.listar_senadores()
    logger.info(f"Encontrados {len(senadores)} senadores")

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

    logger.info(f"{len(nome_para_id)} senadores inseridos/atualizados")
    return nome_para_id

async def seed_despesas_senado(
    pool: asyncpg.Pool,
    senado: SenadoService,
    nome_para_id: dict[str, int],
    anos: list[int],
) -> int:
    """Baixa CSV de despesas do Senado e insere no banco."""
    total = 0

    for ano in anos:
        try:
            despesas = await senado.buscar_despesas_csv(ano)
        except Exception as e:
            logger.warning(f"Erro baixando despesas do Senado {ano}: {e}")
            continue

        sem_match = set()
        for d in despesas:
            nome_upper = (d.get("senador") or "").upper()
            parlamentar_id = nome_para_id.get(nome_upper)

            if not parlamentar_id:
                sem_match.add(nome_upper)
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
                pool,
                id_externo=id_externo,
                parlamentar_id=parlamentar_id,
                ano=d.get("ano") or ano,
                mes=d.get("mes") or 0,
                data_emissao=data_emissao,
                categoria=d.get("tipo_despesa") or "Não informado",
                subcategoria=None,
                fornecedor=d.get("fornecedor"),
                cnpj_cpf=cnpj_cpf,
                documento=d.get("documento"),
                valor_documento=d.get("valor_reembolsado"),
                valor_glosa=0,
                valor_liquido=d.get("valor_reembolsado"),
                url_documento=None,
                lote=None,
                ressarcimento=None,
            )
            total += 1

        if sem_match:
            logger.warning(f"  {ano}: {len(sem_match)} senadores no CSV sem match no banco")

        logger.info(f"  {ano}: {total} despesas inseridas")

    logger.info(f"Total Senado: {total} despesas inseridas/atualizadas")
    return total

async def main():
    parser = argparse.ArgumentParser(description="Popular banco Maracatu com dados do Senado")
    parser.add_argument("--ano", type=int, nargs="+", help="Ano(s) das despesas (default: 2024 2025)")
    args = parser.parse_args()

    anos = args.ano or [2024, 2025]

    pool = await asyncpg.create_pool(dsn=settings.database_url, min_size=2, max_size=5)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            senado = SenadoService(client)
            nome_para_id = await seed_senadores(pool, senado)
            await seed_despesas_senado(pool, senado, nome_para_id, anos)
    finally:
        await pool.close()

    logger.info("Seed Senado concluído!")

if __name__ == "__main__":
    asyncio.run(main())
