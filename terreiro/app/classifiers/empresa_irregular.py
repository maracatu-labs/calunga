"""
Classificador: Empresa Irregular

Verifica se a empresa fornecedora estava inativa/irregular na data da despesa.
Cruza cnpj_cpf da despesa com empresas.situacao_cadastral.
Situações que geram flag: BAIXADA, NULA, SUSPENSA, INAPTA.
Condição temporal: data_situacao < data_emissao.
Cruzamento adicional com sanções CEIS/CNEP/CEPIM.

Referência: PRD seção 3.1 — EmpresaIrregular
"""

import logging
from decimal import Decimal

import asyncpg

from app.classifiers.base import BaseClassifier, Suspeita

logger = logging.getLogger(__name__)

SITUACOES_IRREGULARES = {"BAIXADA", "NULA", "SUSPENSA", "INAPTA"}

class EmpresaIrregular(BaseClassifier):
    name = "empresa_irregular"

    async def classificar(self, pool: asyncpg.Pool) -> list[Suspeita]:

        rows = await pool.fetch(
            """
            SELECT d.id AS despesa_id, d.cnpj_cpf, d.fornecedor, d.data_emissao, d.valor_liquido,
                   e.razao_social, e.situacao_cadastral, e.data_situacao,
                   p.nome AS parlamentar_nome
            FROM despesas d
            JOIN parlamentares p ON d.parlamentar_id = p.id
            JOIN empresas e ON d.cnpj_cpf = e.cnpj
            WHERE e.situacao_cadastral IN ('BAIXADA', 'NULA', 'SUSPENSA', 'INAPTA')
              AND (e.data_situacao IS NULL OR e.data_situacao <= d.data_emissao OR d.data_emissao IS NULL)
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
                    "situacao": row["situacao_cadastral"],
                    "data_situacao": str(row["data_situacao"]) if row["data_situacao"] else None,
                    "motivo": f"Empresa com situação '{row['situacao_cadastral']}' na data da despesa",
                },
            ))

        sancao_rows = await pool.fetch(
            """
            SELECT d.id AS despesa_id, d.cnpj_cpf, d.fornecedor,
                   s_sancao.tipo AS tipo_sancao, s_sancao.orgao_sancionador,
                   p.nome AS parlamentar_nome
            FROM despesas d
            JOIN parlamentares p ON d.parlamentar_id = p.id
            JOIN sancoes s_sancao ON d.cnpj_cpf = s_sancao.cpf_cnpj
            WHERE NOT EXISTS (
                SELECT 1 FROM suspeitas s WHERE s.despesa_id = d.id AND s.classificador = $1
            )
            """,
            self.name,
        )

        for row in sancao_rows:
            suspeitas.append(Suspeita(
                despesa_id=row["despesa_id"],
                classificador=self.name,
                probabilidade=Decimal("1.0"),
                detalhes={
                    "parlamentar": row["parlamentar_nome"],
                    "fornecedor": row["fornecedor"],
                    "cnpj": row["cnpj_cpf"],
                    "tipo_sancao": row["tipo_sancao"],
                    "orgao_sancionador": row["orgao_sancionador"],
                    "motivo": f"Empresa com sanção {row['tipo_sancao']} ({row['orgao_sancionador']})",
                },
            ))

        logger.info(f"{self.name}: {len(suspeitas)} suspeitas encontradas")
        return suspeitas
