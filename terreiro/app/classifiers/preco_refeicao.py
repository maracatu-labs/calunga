"""
Classificador: Preço de Refeição Anômalo

Detecta refeições com preço atipicamente alto para um restaurante.
- Aplica-se a categoria "Alimentação" (subcota 12)
- Exclui hotéis (regex no fornecedor)
- Calcula estatísticas por restaurante (CNPJ)
- K-Means (k=3) para agrupar restaurantes por perfil de preço
- Threshold: média_cluster + 4σ
- Filtra restaurantes com >3 parlamentares e >20 registros

Referência: PRD seção 3.1 — PrecoRefeicaoAnomalo
"""

import logging
import re
from decimal import Decimal

import asyncpg
import numpy as np

from app.classifiers.base import BaseClassifier, Suspeita

logger = logging.getLogger(__name__)

HOTEL_RE = re.compile(r"hote[l|ls|is]", re.IGNORECASE)
MIN_PARLAMENTARES = 3
MIN_REGISTROS = 20

class PrecoRefeicaoAnomalo(BaseClassifier):
    name = "preco_refeicao_anomalo"

    async def classificar(self, pool: asyncpg.Pool) -> list[Suspeita]:

        rows = await pool.fetch(
            """
            SELECT d.id, d.cnpj_cpf, d.fornecedor, d.valor_liquido, d.parlamentar_id,
                   p.nome AS parlamentar_nome
            FROM despesas d
            JOIN parlamentares p ON d.parlamentar_id = p.id
            WHERE d.categoria ILIKE '%aliment%'
              AND d.cnpj_cpf IS NOT NULL
              AND LENGTH(d.cnpj_cpf) = 14
              AND d.valor_liquido > 0
              AND NOT EXISTS (
                  SELECT 1 FROM suspeitas s WHERE s.despesa_id = d.id AND s.classificador = $1
              )
            """,
            self.name,
        )

        if not rows:
            logger.info(f"{self.name}: nenhuma despesa de alimentação para analisar")
            return []

        rows = [r for r in rows if not HOTEL_RE.search(r["fornecedor"] or "")]

        por_cnpj: dict[str, list] = {}
        for r in rows:
            cnpj = r["cnpj_cpf"]
            if cnpj not in por_cnpj:
                por_cnpj[cnpj] = []
            por_cnpj[cnpj].append(r)

        restaurantes_validos = {}
        for cnpj, despesas in por_cnpj.items():
            parlamentares_unicos = len(set(d["parlamentar_id"] for d in despesas))
            if parlamentares_unicos >= MIN_PARLAMENTARES and len(despesas) >= MIN_REGISTROS:
                restaurantes_validos[cnpj] = despesas

        if not restaurantes_validos:
            logger.info(f"{self.name}: nenhum restaurante com amostra suficiente")
            return []

        stats = {}
        for cnpj, despesas in restaurantes_validos.items():
            valores = [float(d["valor_liquido"]) for d in despesas]
            stats[cnpj] = {
                "media": np.mean(valores),
                "std": np.std(valores),
                "fornecedor": despesas[0]["fornecedor"],
            }

        try:
            from sklearn.cluster import KMeans

            medias = np.array([[s["media"]] for s in stats.values()])
            k = min(3, len(medias))
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(medias)

            cluster_stats = {}
            for i in range(k):
                cluster_medias = medias[labels == i].flatten()
                cluster_stats[i] = {
                    "media": np.mean(cluster_medias),
                    "std": np.std(cluster_medias),
                }

            for (_cnpj, s), label in zip(stats.items(), labels, strict=False):
                s["cluster"] = int(label)
                s["cluster_threshold"] = cluster_stats[label]["media"] + 4 * cluster_stats[label]["std"]

        except ImportError:
            logger.warning("scikit-learn não instalado. Usando threshold simples.")
            for _cnpj, s in stats.items():
                s["cluster_threshold"] = s["media"] + 4 * s["std"]

        suspeitas = []
        for cnpj, despesas in restaurantes_validos.items():
            s = stats[cnpj]

            threshold_restaurante = s["media"] + 3 * s["std"]

            threshold_cluster = s.get("cluster_threshold", threshold_restaurante)

            threshold = min(threshold_restaurante, threshold_cluster)

            for d in despesas:
                valor = float(d["valor_liquido"])
                if valor > threshold:
                    distancia = (valor - s["media"]) / s["std"] if s["std"] > 0 else 0
                    probabilidade = min(Decimal("0.99"), Decimal(str(min(1.0, distancia / 10))))

                    suspeitas.append(Suspeita(
                        despesa_id=d["id"],
                        classificador=self.name,
                        probabilidade=probabilidade,
                        detalhes={
                            "parlamentar": d["parlamentar_nome"],
                            "fornecedor": d["fornecedor"],
                            "cnpj": cnpj,
                            "valor": str(d["valor_liquido"]),
                            "media_restaurante": f"{s['media']:.2f}",
                            "threshold": f"{threshold:.2f}",
                            "desvios": f"{distancia:.1f}σ",
                            "motivo": f"Valor R$ {d['valor_liquido']} está {distancia:.1f}σ acima da média (R$ {s['media']:.2f}) do restaurante",
                        },
                    ))

        logger.info(f"{self.name}: {len(suspeitas)} suspeitas em {len(restaurantes_validos)} restaurantes analisados")
        return suspeitas
