"""Endpoints de exportação de dados para pesquisadores."""

import csv
import io
from datetime import date

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.database import get_pool

router = APIRouter(prefix="/v1/exportar", tags=["exportação"])

@router.get("/despesas.csv")
async def exportar_despesas_csv(
    ano: int | None = Query(None),
    uf: str | None = Query(None),
    partido: str | None = Query(None),
    tipo: str | None = Query(None, description="deputado ou senador"),
    limit: int = Query(10000, ge=1, le=100000),
):
    """Exporta despesas em CSV para pesquisadores."""
    pool = get_pool()

    query = """
        SELECT d.id_externo, p.nome AS parlamentar, p.tipo, p.partido, p.uf,
               d.ano, d.mes, d.data_emissao, d.categoria, d.fornecedor,
               d.cnpj_cpf, d.valor_documento, d.valor_glosa, d.valor_liquido,
               d.url_documento
        FROM despesas d
        JOIN parlamentares p ON d.parlamentar_id = p.id
        WHERE 1=1
    """
    params: list = []

    if ano:
        params.append(ano)
        query += f" AND d.ano = ${len(params)}"
    if uf:
        params.append(uf.upper())
        query += f" AND p.uf = ${len(params)}"
    if partido:
        params.append(partido.upper())
        query += f" AND p.partido = ${len(params)}"
    if tipo:
        params.append(tipo)
        query += f" AND p.tipo = ${len(params)}"

    query += " ORDER BY d.ano DESC, d.mes DESC, d.valor_liquido DESC"
    params.append(limit)
    query += f" LIMIT ${len(params)}"

    rows = await pool.fetch(query, *params)

    output = io.StringIO()
    writer = csv.writer(output)
    if rows:
        writer.writerow(rows[0].keys())
        for row in rows:
            writer.writerow([str(v) if v is not None else "" for v in row.values()])

    output.seek(0)
    filename = f"maracatu_despesas_{ano or 'todos'}_{date.today().isoformat()}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@router.get("/suspeitas.csv")
async def exportar_suspeitas_csv(
    classificador: str | None = Query(None),
    ano: int | None = Query(None),
    limit: int = Query(10000, ge=1, le=100000),
):
    """Exporta suspeitas em CSV."""
    pool = get_pool()

    query = """
        SELECT s.classificador, s.probabilidade, s.detalhes,
               d.ano, d.mes, d.categoria, d.fornecedor, d.cnpj_cpf, d.valor_liquido,
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
    if ano:
        params.append(ano)
        query += f" AND d.ano = ${len(params)}"

    query += " ORDER BY s.probabilidade DESC, d.valor_liquido DESC"
    params.append(limit)
    query += f" LIMIT ${len(params)}"

    rows = await pool.fetch(query, *params)

    output = io.StringIO()
    writer = csv.writer(output)
    if rows:
        writer.writerow(rows[0].keys())
        for row in rows:
            writer.writerow([str(v) if v is not None else "" for v in row.values()])

    output.seek(0)
    filename = f"maracatu_suspeitas_{date.today().isoformat()}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@router.get("/parlamentares.csv")
async def exportar_parlamentares_csv(
    tipo: str | None = Query(None),
):
    """Exporta lista de parlamentares em CSV."""
    pool = get_pool()

    query = "SELECT id_externo, tipo, nome, partido, uf, legislatura, email, situacao FROM parlamentares WHERE 1=1"
    params: list = []

    if tipo:
        params.append(tipo)
        query += f" AND tipo = ${len(params)}"

    query += " ORDER BY nome"

    rows = await pool.fetch(query, *params)

    output = io.StringIO()
    writer = csv.writer(output)
    if rows:
        writer.writerow(rows[0].keys())
        for row in rows:
            writer.writerow([str(v) if v is not None else "" for v in row.values()])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="maracatu_parlamentares.csv"'},
    )
