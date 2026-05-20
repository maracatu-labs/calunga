"""Endpoints de suspeitas com validação human-in-the-loop."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.database import get_pool

router = APIRouter(prefix="/v1/suspeitas", tags=["suspeitas"])

@router.get("")
async def listar_suspeitas(
    classificador: str | None = Query(None),
    verificada: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    pool = get_pool()
    query = """
        SELECT s.id, s.classificador, s.probabilidade, s.detalhes, s.verificada,
               s.validada_por, s.feedback, s.created_at,
               d.categoria, d.fornecedor, d.valor_liquido, d.ano, d.mes,
               p.nome AS parlamentar, p.partido, p.uf
        FROM suspeitas s
        JOIN despesas d ON s.despesa_id = d.id
        JOIN parlamentares p ON d.parlamentar_id = p.id
        WHERE 1=1
    """
    params: list = []

    if classificador:
        params.append(classificador)
        query += f" AND s.classificador = ${len(params)}"
    if verificada is not None:
        params.append(verificada)
        query += f" AND s.verificada = ${len(params)}"

    query += " ORDER BY s.probabilidade DESC, d.valor_liquido DESC"
    params.append(limit)
    query += f" LIMIT ${len(params)}"
    params.append(offset)
    query += f" OFFSET ${len(params)}"

    rows = await pool.fetch(query, *params)
    return {"data": [dict(r) for r in rows], "total": len(rows)}

@router.get("/estatisticas")
async def estatisticas_suspeitas():
    pool = get_pool()
    stats = await pool.fetch(
        """
        SELECT classificador,
               COUNT(*) AS total,
               COUNT(*) FILTER (WHERE verificada = TRUE) AS verificadas,
               COUNT(*) FILTER (WHERE verificada = FALSE) AS pendentes
        FROM suspeitas
        GROUP BY classificador
        ORDER BY total DESC
        """
    )
    return {"data": [dict(r) for r in stats]}

class ValidarSuspeitaRequest(BaseModel):
    verificada: bool
    feedback: str | None = None
    validada_por: str | None = None

@router.patch("/{suspeita_id}")
async def validar_suspeita(suspeita_id: int, body: ValidarSuspeitaRequest):
    """Valida ou rejeita uma suspeita (human-in-the-loop)."""
    pool = get_pool()

    result = await pool.execute(
        """
        UPDATE suspeitas
        SET verificada = $1, feedback = $2, validada_por = $3, validada_em = NOW()
        WHERE id = $4
        """,
        body.verificada,
        body.feedback,
        body.validada_por or "anonymous",
        suspeita_id,
    )

    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Suspeita não encontrada")

    return {"ok": True, "id": suspeita_id, "verificada": body.verificada}
