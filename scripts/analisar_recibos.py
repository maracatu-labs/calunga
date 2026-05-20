"""
Analisa recibos de despesas parlamentares via OCR + LLM.

Uso:
    python scripts/analisar_recibos.py --limit 10
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, "/app")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "terreiro"))

import asyncpg

from app.config import settings
from app.services.ocr import process_receipt

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

async def main():
    parser = argparse.ArgumentParser(description="Analisar recibos via OCR + LLM")
    parser.add_argument("--limit", type=int, default=10, help="Número de recibos para analisar")
    args = parser.parse_args()

    pool = await asyncpg.create_pool(dsn=settings.database_url, min_size=1, max_size=3)

    try:

        rows = await pool.fetch(
            """
            SELECT d.id, d.url_documento, d.fornecedor, d.valor_liquido, d.categoria,
                   p.nome AS parlamentar_nome
            FROM despesas d
            JOIN parlamentares p ON d.parlamentar_id = p.id
            WHERE d.url_documento IS NOT NULL
              AND d.url_documento != ''
              AND d.categoria ILIKE '%aliment%'
            ORDER BY d.valor_liquido DESC NULLS LAST
            LIMIT $1
            """,
            args.limit,
        )

        logger.info(f"Analisando {len(rows)} recibos...")
        irregulares = 0

        for row in rows:
            logger.info(f"  {row['parlamentar_nome']}: {row['fornecedor']} (R$ {row['valor_liquido']})")

            result = await process_receipt(row["url_documento"])
            if not result:
                logger.info("    Sem PDF disponível")
                continue

            if result.get("needs_vision_ocr"):
                logger.info("    PDF é imagem (precisa Vision OCR)")
                continue

            if result.get("tem_alcool"):
                logger.warning(f"    ⚠ ÁLCOOL DETECTADO: {row['fornecedor']}")
                irregulares += 1

            if result.get("irregularidades"):
                for irr in result["irregularidades"]:
                    logger.warning(f"    ⚠ {irr}")
                irregulares += 1

            if result.get("tem_alcool") or result.get("irregularidades"):
                await pool.execute(
                    """
                    INSERT INTO suspeitas (despesa_id, classificador, probabilidade, detalhes)
                    VALUES ($1, 'ocr_recibo', 0.8, $2::jsonb)
                    ON CONFLICT DO NOTHING
                    """,
                    row["id"],
                    json.dumps(result, ensure_ascii=False, default=str),
                )

        logger.info(f"Concluído: {irregulares} irregularidades encontradas em {len(rows)} recibos")

    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
