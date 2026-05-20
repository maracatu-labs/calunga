"""
Roda todos os classificadores sobre as despesas e persiste suspeitas.

Uso:
    python scripts/analisar_suspeitas.py
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, "/app")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "terreiro"))

import asyncpg

from app.config import settings
from app.classifiers.cnpj_cpf_invalido import CNPJCPFInvalido
from app.classifiers.limite_subcota import LimiteSubcotaMensal
from app.classifiers.empresa_irregular import EmpresaIrregular
from app.classifiers.despesa_eleitoral import DespesaEleitoral
from app.classifiers.despesa_fim_de_semana import DespesaFimDeSemana
from app.classifiers.preco_refeicao import PrecoRefeicaoAnomalo

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ALL_CLASSIFIERS = [
    CNPJCPFInvalido(),
    LimiteSubcotaMensal(),
    EmpresaIrregular(),
    DespesaEleitoral(),
    DespesaFimDeSemana(),
    PrecoRefeicaoAnomalo(),
]

async def main():
    pool = await asyncpg.create_pool(dsn=settings.database_url, min_size=2, max_size=5)

    try:
        total = 0
        for clf in ALL_CLASSIFIERS:
            logger.info(f"Rodando classificador: {clf.name}")
            suspeitas = await clf.classificar(pool)

            for s in suspeitas:
                await pool.execute(
                    """
                    INSERT INTO suspeitas (despesa_id, classificador, probabilidade, detalhes)
                    VALUES ($1, $2, $3, $4::jsonb)
                    ON CONFLICT DO NOTHING
                    """,
                    s.despesa_id,
                    s.classificador,
                    s.probabilidade,
                    json.dumps(s.detalhes, ensure_ascii=False),
                )
                total += 1

        logger.info(f"Total: {total} suspeitas inseridas")

    finally:
        await pool.close()

    logger.info("Análise concluída!")

if __name__ == "__main__":
    asyncio.run(main())
