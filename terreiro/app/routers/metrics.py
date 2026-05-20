"""Endpoint de metricas simples (snapshot de contadores + latencias).

Exposto em /v1/metrics. Hoje publico (sem auth); em producao convem
adicionar um token ou restringir por IP via Caddy.
"""

from fastapi import APIRouter

from app.metrics import snapshot

router = APIRouter(prefix="/v1", tags=["metrics"])

@router.get("/metrics")
async def get_metrics():
    data = await snapshot()
    return {"metrics": data}
