"""
Classificador: Despesa Eleitoral

Detecta despesas feitas a empresas registradas como candidatura política.
Verifica natureza_juridica == "409-0" na tabela empresas.

Referência: PRD seção 3.1 — DespesaEleitoral
"""

import logging
from decimal import Decimal

import asyncpg

from app.classifiers.base import BaseClassifier, Suspeita

logger = logging.getLogger(__name__)

class DespesaEleitoral(BaseClassifier):
    name = "despesa_eleitoral"

    async def classificar(self, pool: asyncpg.Pool) -> list[Suspeita]:
        rows = await pool.fetch(
            """
            SELECT d.id AS despesa_id, d.cnpj_cpf, d.fornecedor, d.valor_liquido,
                   d.data_emissao, d.categoria,
                   e.razao_social, e.natureza_juridica,
                   p.nome AS parlamentar_nome
            FROM despesas d
            JOIN parlamentares p ON d.parlamentar_id = p.id
            JOIN empresas e ON d.cnpj_cpf = e.cnpj
            WHERE e.natureza_juridica LIKE '409%'
              AND NOT EXISTS (
                  SELECT 1 FROM suspeitas s WHERE s.despesa_id = d.id AND s.classificador = $1
              )
            """,
            self.name,
        )

        suspeitas = []
        for row in rows:
            suspeitas.append(Suspeita(
                despesa_id=row["despesa_id"],
                classificador=self.name,
                probabilidade=Decimal("1.0"),
                detalhes={
                    "parlamentar": row["parlamentar_nome"],
                    "fornecedor": row["fornecedor"],
                    "cnpj": row["cnpj_cpf"],
                    "razao_social": row["razao_social"],
                    "natureza_juridica": row["natureza_juridica"],
                    "motivo": "Pagamento a entidade registrada como candidatura política",
                },
            ))

        logger.info(f"{self.name}: {len(suspeitas)} suspeitas encontradas")
        return suspeitas
