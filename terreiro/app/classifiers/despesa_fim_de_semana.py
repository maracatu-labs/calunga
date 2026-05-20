"""
Classificador: Despesa em Fim de Semana

Detecta gastos em sábados, domingos e feriados nacionais.
Aplica-se principalmente a alimentação e combustível.
Probabilidade baixa (indicativo, não conclusivo).

Referência: PRD seção 3.1 — DespesaFimDeSemana
"""

import logging
from datetime import date
from decimal import Decimal

import asyncpg

from app.classifiers.base import BaseClassifier, Suspeita

logger = logging.getLogger(__name__)

FERIADOS_FIXOS = [
    (1, 1),
    (21, 4),
    (1, 5),
    (7, 9),
    (12, 10),
    (2, 11),
    (15, 11),
    (25, 12),
]

def _is_feriado(d: date) -> bool:
    return (d.day, d.month) in FERIADOS_FIXOS

def _is_fim_de_semana_ou_feriado(d: date) -> str | None:
    if d.weekday() == 5:
        return "sábado"
    if d.weekday() == 6:
        return "domingo"
    if _is_feriado(d):
        return "feriado nacional"
    return None

class DespesaFimDeSemana(BaseClassifier):
    name = "despesa_fim_de_semana"

    async def classificar(self, pool: asyncpg.Pool) -> list[Suspeita]:
        rows = await pool.fetch(
            """
            SELECT d.id, d.data_emissao, d.categoria, d.fornecedor, d.valor_liquido,
                   p.nome AS parlamentar_nome
            FROM despesas d
            JOIN parlamentares p ON d.parlamentar_id = p.id
            WHERE d.data_emissao IS NOT NULL
              AND EXTRACT(DOW FROM d.data_emissao) IN (0, 6)
              AND NOT EXISTS (
                  SELECT 1 FROM suspeitas s WHERE s.despesa_id = d.id AND s.classificador = $1
              )
            """,
            self.name,
        )

        suspeitas = []
        for row in rows:
            dia_tipo = _is_fim_de_semana_ou_feriado(row["data_emissao"])
            if not dia_tipo:
                continue

            suspeitas.append(Suspeita(
                despesa_id=row["id"],
                classificador=self.name,
                probabilidade=Decimal("0.3"),
                detalhes={
                    "parlamentar": row["parlamentar_nome"],
                    "data": str(row["data_emissao"]),
                    "dia": dia_tipo,
                    "categoria": row["categoria"],
                    "fornecedor": row["fornecedor"],
                    "valor": str(row["valor_liquido"]) if row["valor_liquido"] else None,
                    "motivo": f"Despesa emitida em {dia_tipo} ({row['data_emissao'].strftime('%d/%m/%Y')})",
                },
            ))

        logger.info(f"{self.name}: {len(suspeitas)} suspeitas encontradas")
        return suspeitas
