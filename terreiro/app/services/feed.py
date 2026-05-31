"""Serviço para publicar eventos no feed a partir do chat."""

import logging
import uuid

from app.database import get_pool
from app.queries.feed import publicar_evento

logger = logging.getLogger(__name__)

async def publicar_descoberta_chat(
    *,
    tipo: str,
    categoria: str,
    titulo: str,
    descricao: str,
    dados: dict | None = None,
    referencia_tipo: str | None = None,
    referencia_id: uuid.UUID | str | None = None,
    relevancia: float = 0.6,
) -> bool:
    """Publica uma descoberta feita por cidadão no chat.
    Retorna True se publicou, False se já existia."""
    try:
        pool = get_pool()
        result = await publicar_evento(
            pool,
            tipo=tipo,
            categoria=categoria,
            origem="chat",
            titulo=titulo,
            descricao=descricao,
            dados=dados,
            referencia_tipo=referencia_tipo,
            referencia_id=referencia_id,
            relevancia=relevancia,
        )
        return result is not None
    except Exception as e:
        logger.warning(f"Erro publicando no feed: {e}")
        return False
