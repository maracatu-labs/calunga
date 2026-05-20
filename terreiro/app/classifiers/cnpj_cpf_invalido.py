"""
Classificador: CNPJ/CPF Inválido

Valida os dígitos verificadores de CNPJ/CPF dos fornecedores.
Se nem CNPJ nem CPF são válidos → flagged como suspeito.
Probabilidade: 1.0 (binário).

Referência: PRD seção 3.1 — CNPJCPFInvalido
"""

import logging
from decimal import Decimal

import asyncpg

from app.classifiers.base import BaseClassifier, Suspeita

logger = logging.getLogger(__name__)

def _validate_cpf(cpf: str) -> bool:
    """Valida CPF usando módulo 11."""
    cpf = cpf.zfill(11)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    for i in range(9, 11):
        total = sum(int(cpf[j]) * ((i + 1) - j) for j in range(i))
        digit = (total * 10) % 11
        if digit == 10:
            digit = 0
        if int(cpf[i]) != digit:
            return False
    return True

def _validate_cnpj(cnpj: str) -> bool:
    """Valida CNPJ usando módulo 11."""
    cnpj = cnpj.zfill(14)
    if len(cnpj) != 14:
        return False

    weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    total = sum(int(cnpj[i]) * weights1[i] for i in range(12))
    digit1 = 11 - (total % 11)
    if digit1 >= 10:
        digit1 = 0
    if int(cnpj[12]) != digit1:
        return False

    total = sum(int(cnpj[i]) * weights2[i] for i in range(13))
    digit2 = 11 - (total % 11)
    if digit2 >= 10:
        digit2 = 0
    return int(cnpj[13]) == digit2

class CNPJCPFInvalido(BaseClassifier):
    name = "cnpj_cpf_invalido"

    async def classificar(self, pool: asyncpg.Pool) -> list[Suspeita]:

        rows = await pool.fetch(
            """
            SELECT d.id, d.cnpj_cpf, d.fornecedor
            FROM despesas d
            WHERE d.cnpj_cpf IS NOT NULL
              AND d.cnpj_cpf != ''
              AND NOT EXISTS (
                  SELECT 1 FROM suspeitas s
                  WHERE s.despesa_id = d.id AND s.classificador = $1
              )
            """,
            self.name,
        )

        suspeitas = []
        for row in rows:
            doc = row["cnpj_cpf"].strip()
            if not doc:
                continue

            is_valid = False
            doc_type = None

            digits_only = "".join(c for c in doc if c.isdigit())

            if len(digits_only) == 14:
                is_valid = _validate_cnpj(digits_only)
                doc_type = "CNPJ"
            elif len(digits_only) == 11:
                is_valid = _validate_cpf(digits_only)
                doc_type = "CPF"
            elif len(digits_only) < 11:

                is_valid = _validate_cpf(digits_only.zfill(11))
                doc_type = "CPF"
            else:

                is_valid = _validate_cnpj(digits_only.zfill(14))
                doc_type = "CNPJ"

            if not is_valid:
                suspeitas.append(Suspeita(
                    despesa_id=row["id"],
                    classificador=self.name,
                    probabilidade=Decimal("1.0"),
                    detalhes={
                        "documento": doc,
                        "tipo_esperado": doc_type,
                        "fornecedor": row["fornecedor"],
                        "motivo": f"{doc_type} inválido: dígitos verificadores não conferem",
                    },
                ))

        logger.info(f"{self.name}: {len(suspeitas)} suspeitas em {len(rows)} despesas analisadas")
        return suspeitas
