from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

import asyncpg

@dataclass
class Suspeita:
    despesa_id: int
    classificador: str
    probabilidade: Decimal
    detalhes: dict

class BaseClassifier(ABC):
    name: str

    @abstractmethod
    async def classificar(self, pool: asyncpg.Pool) -> list[Suspeita]:
        """Analisa despesas e retorna lista de suspeitas encontradas."""
        ...
