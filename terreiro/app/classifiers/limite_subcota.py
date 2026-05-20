"""
Classificador: Limite de Subcota Mensal

Detecta quando um parlamentar ultrapassa o limite mensal de uma subcota.
Agrupa despesas por (parlamentar_id, ano, mes), calcula soma acumulada.
Se cumsum > limite → flagged.

Referência: PRD seção 3.1 — LimiteSubcotaMensal
"""

import logging
from datetime import date
from decimal import Decimal

import asyncpg

from app.classifiers.base import BaseClassifier, Suspeita

logger = logging.getLogger(__name__)

LIMITES = [

    ("LOCAÇÃO OU FRETAMENTO DE VEÍCULOS", date(2013, 12, 1), date(2015, 3, 31), Decimal("10000")),
    ("LOCAÇÃO OU FRETAMENTO DE VEÍCULOS", date(2015, 4, 1), date(2017, 4, 30), Decimal("10900")),
    ("LOCAÇÃO OU FRETAMENTO DE VEÍCULOS", date(2017, 5, 1), None, Decimal("12713")),

    ("TÁXI, PEDÁGIO E ESTACIONAMENTO", date(2013, 12, 1), date(2015, 3, 31), Decimal("2500")),
    ("TÁXI, PEDÁGIO E ESTACIONAMENTO", date(2015, 4, 1), None, Decimal("2700")),

    ("COMBUSTÍVEIS E LUBRIFICANTES", date(2009, 7, 1), date(2015, 3, 31), Decimal("4500")),
    ("COMBUSTÍVEIS E LUBRIFICANTES", date(2015, 4, 1), date(2015, 8, 31), Decimal("4900")),
    ("COMBUSTÍVEIS E LUBRIFICANTES", date(2015, 9, 1), None, Decimal("6000")),

    ("SERVIÇO DE SEGURANÇA", date(2009, 7, 1), date(2014, 4, 30), Decimal("4500")),
    ("SERVIÇO DE SEGURANÇA", date(2014, 5, 1), date(2015, 3, 31), Decimal("8000")),
    ("SERVIÇO DE SEGURANÇA", date(2015, 4, 1), None, Decimal("8700")),

    ("PARTICIPAÇÃO EM CURSO", date(2015, 10, 1), None, Decimal("7697.16")),
]

def _get_limite(categoria: str, ano: int, mes: int) -> Decimal | None:
    """Retorna o limite mensal para uma categoria/período, ou None se não há limite."""
    ref_date = date(ano, mes, 1)
    cat_upper = (categoria or "").upper()

    for pattern, inicio, fim, limite in LIMITES:
        if pattern in cat_upper:
            if ref_date >= inicio and (fim is None or ref_date <= fim):
                return limite
    return None

class LimiteSubcotaMensal(BaseClassifier):
    name = "limite_subcota_mensal"

    async def classificar(self, pool: asyncpg.Pool) -> list[Suspeita]:

        rows = await pool.fetch(
            """
            SELECT
                d.parlamentar_id,
                p.nome AS parlamentar_nome,
                d.ano,
                d.mes,
                d.categoria,
                SUM(d.valor_liquido) AS total_mensal,
                array_agg(d.id) AS despesa_ids
            FROM despesas d
            JOIN parlamentares p ON d.parlamentar_id = p.id
            WHERE d.valor_liquido > 0
            GROUP BY d.parlamentar_id, p.nome, d.ano, d.mes, d.categoria
            ORDER BY d.parlamentar_id, d.ano, d.mes
            """
        )

        analisados = set()
        existing = await pool.fetch(
            "SELECT despesa_id FROM suspeitas WHERE classificador = $1",
            self.name,
        )
        for r in existing:
            analisados.add(r["despesa_id"])

        suspeitas = []
        for row in rows:
            limite = _get_limite(row["categoria"], row["ano"], row["mes"])
            if limite is None:
                continue

            total = row["total_mensal"] or Decimal("0")
            if total <= limite:
                continue

            for despesa_id in row["despesa_ids"]:
                if despesa_id in analisados:
                    continue
                analisados.add(despesa_id)

                suspeitas.append(Suspeita(
                    despesa_id=despesa_id,
                    classificador=self.name,
                    probabilidade=Decimal("1.0"),
                    detalhes={
                        "parlamentar": row["parlamentar_nome"],
                        "ano": row["ano"],
                        "mes": row["mes"],
                        "categoria": row["categoria"],
                        "total_mensal": str(total),
                        "limite": str(limite),
                        "excesso": str(total - limite),
                        "motivo": f"Total mensal R$ {total:,.2f} excede limite de R$ {limite:,.2f}",
                    },
                ))

        logger.info(f"{self.name}: {len(suspeitas)} suspeitas encontradas")
        return suspeitas
