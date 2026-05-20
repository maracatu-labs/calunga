"""Service para gerar embeddings com BGE-M3 rodando localmente via sentence-transformers.

A API de inferencia publica do HuggingFace (api-inference.huggingface.co) foi
descontinuada em 2026. A alternativa e carregar o modelo localmente. O BGE-M3
e um modelo multilingue otimizado para portugues com 1024 dim.

A primeira chamada carrega o modelo em memoria (~2 GB). Subsequentes sao rapidas.
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1024
MODEL_NAME = "BAAI/bge-m3"

_model = None
_model_lock = asyncio.Lock()

async def _get_model():
    """Carrega o modelo uma unica vez (singleton)."""
    global _model
    if _model is None:
        async with _model_lock:
            if _model is None:
                logger.info(f"Carregando modelo {MODEL_NAME} localmente...")

                from sentence_transformers import SentenceTransformer

                _model = await asyncio.to_thread(SentenceTransformer, MODEL_NAME)
                logger.info("Modelo carregado")
    return _model

async def generate_embedding(text: str) -> Optional[list[float]]:
    """Gera embedding para um unico texto."""
    if not text:
        return None
    try:
        model = await _get_model()
        vec = await asyncio.to_thread(
            model.encode, text, normalize_embeddings=True, show_progress_bar=False
        )
        return vec.tolist()[:EMBEDDING_DIM]
    except Exception as e:
        logger.warning(f"Embedding error: {e}")
        return None

async def generate_embeddings_batch(texts: list[str]) -> list[Optional[list[float]]]:
    """Gera embeddings em batch. Retorna uma lista do mesmo tamanho da entrada."""
    if not texts:
        return []
    try:
        model = await _get_model()
        vecs = await asyncio.to_thread(
            model.encode,
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=min(32, len(texts)),
        )
        return [v.tolist()[:EMBEDDING_DIM] for v in vecs]
    except Exception as e:
        logger.warning(f"Batch embedding error: {e}")
        return [None] * len(texts)
