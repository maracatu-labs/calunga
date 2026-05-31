import uuid

from fastapi import APIRouter, HTTPException, Query

from app.database import get_pool
from app.queries import despesas as despesas_q
from app.queries import parlamentares as parlamentares_q
from app.schemas.despesa import DespesaList, DespesaResponse
from app.schemas.parlamentar import ParlamentarList, ParlamentarResponse

router = APIRouter(prefix="/v1/senadores", tags=["senadores"])

@router.get("", response_model=ParlamentarList)
async def listar_senadores(
    uf: str | None = Query(None, description="Sigla do estado (ex: SP, RJ)"),
    partido: str | None = Query(None, description="Sigla do partido (ex: PL, PT)"),
    nome: str | None = Query(None, description="Busca por nome (parcial)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    pool = get_pool()
    rows = await parlamentares_q.listar_parlamentares(
        pool, tipo="senador", uf=uf, partido=partido, nome=nome, limit=limit, offset=offset
    )
    data = [ParlamentarResponse(**dict(r)) for r in rows]
    return ParlamentarList(data=data, total=len(data))

@router.get("/{senador_id}", response_model=ParlamentarResponse)
async def buscar_senador(senador_id: uuid.UUID):
    pool = get_pool()
    row = await parlamentares_q.buscar_parlamentar(pool, senador_id)
    if not row:
        raise HTTPException(status_code=404, detail="Senador não encontrado")
    return ParlamentarResponse(**dict(row))

@router.get("/{senador_id}/despesas", response_model=DespesaList)
async def listar_despesas_senador(
    senador_id: uuid.UUID,
    ano: int | None = Query(None, description="Ano (ex: 2025)"),
    mes: int | None = Query(None, ge=1, le=12, description="Mês (1-12)"),
    categoria: str | None = Query(None, description="Categoria da despesa"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    pool = get_pool()

    parlamentar = await parlamentares_q.buscar_parlamentar(pool, senador_id)
    if not parlamentar:
        raise HTTPException(status_code=404, detail="Senador não encontrado")

    rows = await despesas_q.listar_despesas(
        pool, parlamentar_id=senador_id, ano=ano, mes=mes, categoria=categoria, limit=limit, offset=offset
    )
    data = [DespesaResponse(**dict(r)) for r in rows]
    return DespesaList(data=data, total=len(data))
