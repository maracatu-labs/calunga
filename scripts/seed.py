"""
Seed script: popular banco com deputados + despesas reais da Câmara dos Deputados.

Uso:
    python scripts/seed.py                  # legislatura atual, anos 2024-2025
    python scripts/seed.py --ano 2025       # só 2025
    python scripts/seed.py --limit 10       # só 10 deputados (para teste rápido)
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
from app.services.camara import CamaraService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def _to_int(val, default=None) -> int | None:
    if val is None or val == "":
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def _to_float(val, default=None) -> float | None:
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def _clean_cnpj(val) -> str | None:
    if not val:
        return None
    return str(val).replace(".", "").replace("/", "").replace("-", "").strip() or None

DEPUTADOS_DESTAQUE = [
    "Nikolas Ferreira",
    "Tabata Amaral",
    "Guilherme Boulos",
    "Eduardo Bolsonaro",
    "Kim Kataguiri",
    "Erika Hilton",
    "Marcelo Freixo",
    "Carla Zambelli",
    "André Janones",
    "Orlando Silva",
]

async def seed_deputados(pool: asyncpg.Pool, camara: CamaraService, limit: int | None = None) -> list[dict]:
    """Busca deputados da legislatura atual e insere no banco."""
    legislatura = await camara.buscar_legislatura_atual()
    logger.info(f"Legislatura atual: {legislatura}")

    deputados = await camara.listar_todos_deputados(legislatura=legislatura)
    logger.info(f"Encontrados {len(deputados)} deputados")

    if limit:

        nomes_destaque = {n.lower() for n in DEPUTADOS_DESTAQUE}
        destaque = [d for d in deputados if d.get("nome", "").lower() in nomes_destaque]
        outros = [d for d in deputados if d.get("nome", "").lower() not in nomes_destaque]
        deputados = (destaque + outros)[:limit]
        logger.info(f"Limitando a {limit} deputados ({len(destaque)} de destaque)")

    inseridos = []
    for dep in deputados:

        await inserir_raw(pool, fonte="camara", tipo="deputados", payload=dep)

        record = await upsert_parlamentar(
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
        inseridos.append({"id": record["id"], "id_externo": dep["id"], "nome": dep["nome"]})

    logger.info(f"{len(inseridos)} deputados inseridos/atualizados")
    return inseridos

async def seed_despesas(
    pool: asyncpg.Pool,
    camara: CamaraService,
    deputados: list[dict],
    anos: list[int],
) -> int:
    """Busca despesas de cada deputado e insere no banco."""
    total = 0

    for i, dep in enumerate(deputados, 1):
        dep_id_externo = dep["id_externo"]
        dep_id_interno = dep["id"]
        logger.info(f"[{i}/{len(deputados)}] Buscando despesas de {dep['nome']} (ID {dep_id_externo})")

        for ano in anos:
            try:
                despesas = await camara.buscar_todas_despesas(dep_id_externo, ano=ano)
            except httpx.HTTPStatusError as e:
                logger.warning(f"Erro buscando despesas de {dep['nome']} em {ano}: {e}")
                continue

            for d in despesas:

                await inserir_raw(pool, fonte="camara", tipo="despesas", payload=d)

                id_externo = f"camara-{dep_id_externo}-{d.get('codDocumento', '')}-{d.get('numDocumento', '')}-{ano}-{d.get('mes', '')}"

                data_emissao = None
                if d.get("dataDocumento"):
                    try:
                        data_emissao = date.fromisoformat(d["dataDocumento"])
                    except (ValueError, TypeError):
                        pass

                await upsert_despesa(
                    pool,
                    id_externo=id_externo,
                    parlamentar_id=dep_id_interno,
                    ano=_to_int(d.get("ano"), ano),
                    mes=_to_int(d.get("mes"), 0),
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

            if despesas:
                logger.info(f"  {ano}: {len(despesas)} despesas")

    logger.info(f"Total: {total} despesas inseridas/atualizadas")
    return total

async def main():
    parser = argparse.ArgumentParser(description="Popular banco Maracatu com dados da Câmara")
    parser.add_argument("--ano", type=int, nargs="+", help="Ano(s) das despesas (default: 2024 2025)")
    parser.add_argument("--limit", type=int, help="Limitar número de deputados (para teste)")
    args = parser.parse_args()

    anos = args.ano or [2024, 2025]

    pool = await asyncpg.create_pool(dsn=settings.database_url, min_size=2, max_size=5)

    try:
        async with httpx.AsyncClient(
            base_url=settings.camara_api_url,
            timeout=30.0,
            headers={"Accept": "application/json"},
        ) as client:
            camara = CamaraService(client)
            deputados = await seed_deputados(pool, camara, limit=args.limit)
            await seed_despesas(pool, camara, deputados, anos)

    finally:
        await pool.close()

    logger.info("Seed concluído!")

if __name__ == "__main__":
    asyncio.run(main())
