import hashlib
import json

import asyncpg

async def inserir_raw(
    pool: asyncpg.Pool,
    fonte: str,
    tipo: str,
    payload: dict,
) -> asyncpg.Record | None:
    payload_json = json.dumps(payload, sort_keys=True, default=str)
    hash_payload = hashlib.sha256(payload_json.encode()).hexdigest()

    return await pool.fetchrow(
        """
        INSERT INTO raw_ingestao (fonte, tipo, payload, hash_payload)
        VALUES ($1, $2, $3::jsonb, $4)
        ON CONFLICT (hash_payload) DO NOTHING
        RETURNING *
        """,
        fonte,
        tipo,
        payload_json,
        hash_payload,
    )

async def marcar_processado(pool: asyncpg.Pool, raw_id: int) -> None:
    await pool.execute(
        "UPDATE raw_ingestao SET processado = TRUE WHERE id = $1",
        raw_id,
    )
