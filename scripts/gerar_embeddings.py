"""
Gera embeddings para despesas (busca semântica / RAG).

Uso:
    python scripts/gerar_embeddings.py
    python scripts/gerar_embeddings.py --limit 1000
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
from app.services.embeddings import generate_embeddings_batch

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BATCH_SIZE = 32

def despesa_to_text(row) -> str:
    """Converte uma despesa em texto para embedding."""
    parts = [
        f"Deputado/Senador {row['parlamentar_nome']} ({row['partido']}/{row['uf']})",
        f"gastou R$ {row['valor_liquido']}" if row["valor_liquido"] else "",
        f"em {row['categoria']}" if row["categoria"] else "",
        f"no fornecedor {row['fornecedor']}" if row["fornecedor"] else "",
        f"em {row['mes']}/{row['ano']}" if row["ano"] else "",
    ]
    return " ".join(p for p in parts if p)

async def main():
    parser = argparse.ArgumentParser(description="Gerar embeddings para despesas")
    parser.add_argument("--limit", type=int, help="Limitar número de despesas")
    args = parser.parse_args()

    pool = await asyncpg.create_pool(dsn=settings.database_url, min_size=2, max_size=5)

    try:

        limit_clause = f"LIMIT {args.limit}" if args.limit else ""
        rows = await pool.fetch(
            f"""
            SELECT d.id, d.ano, d.mes, d.categoria, d.fornecedor, d.valor_liquido,
                   p.nome AS parlamentar_nome, p.partido, p.uf
            FROM despesas d
            JOIN parlamentares p ON d.parlamentar_id = p.id
            WHERE NOT EXISTS (
                SELECT 1 FROM embeddings e WHERE e.tipo = 'despesa' AND e.referencia_id = d.id
            )
            ORDER BY d.id
            {limit_clause}
            """
        )

        logger.info(f"{len(rows)} despesas sem embedding")

        total = 0
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i:i + BATCH_SIZE]
            texts = [despesa_to_text(r) for r in batch]

            embeddings = await generate_embeddings_batch(texts)

            for row, text, emb in zip(batch, texts, embeddings):
                if emb is None:
                    continue

                await pool.execute(
                    """
                    INSERT INTO embeddings (tipo, referencia_id, conteudo_texto, embedding)
                    VALUES ('despesa', $1, $2, $3::vector)
                    """,
                    row["id"],
                    text,
                    json.dumps(emb),
                )
                total += 1

            logger.info(f"  Batch {i // BATCH_SIZE + 1}: {total} embeddings gerados")
            await asyncio.sleep(1)

    finally:
        await pool.close()

    logger.info(f"Total: {total} embeddings gerados")

if __name__ == "__main__":
    asyncio.run(main())
