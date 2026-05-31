"""Endpoint público do feed de eventos."""

import json
import uuid

from fastapi import APIRouter, HTTPException, Query

from app.database import get_pool
from app.queries.feed import contar_feed, get_evento_por_id, listar_feed

router = APIRouter(prefix="/v1/feed", tags=["feed"])

def _parse_dados(raw) -> dict:
    if raw is None:
        return {}
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except ValueError:
            return {}
    return raw

@router.get("")
async def get_feed(
    tipo: str | None = Query(None, description="Filtro por tipo: suspeita, votacao, emenda_pix, empresa_sancionada"),
    categoria: str | None = Query(None, description="Filtro por categoria: irregularidade, congresso, governo_federal"),
    origem: str | None = Query(None, description="Filtro por origem: dagster, chat"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    pool = get_pool()
    eventos = await listar_feed(pool, tipo=tipo, categoria=categoria, origem=origem, limit=limit, offset=offset)
    total = await contar_feed(pool, tipo=tipo, categoria=categoria, origem=origem)

    return {
        "eventos": [
            {
                "id": e["id"],
                "tipo": e["tipo"],
                "categoria": e["categoria"],
                "origem": e["origem"],
                "titulo": e["titulo"],
                "descricao": e["descricao"],
                "dados": _parse_dados(e["dados"]),
                "relevancia": float(e["relevancia"]) if e["relevancia"] else 0.5,
                "created_at": e["created_at"].isoformat(),
            }
            for e in eventos
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }

@router.get("/{evento_id}")
async def get_feed_evento(evento_id: uuid.UUID):
    pool = get_pool()
    evento = await get_evento_por_id(pool, evento_id)
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    return evento
