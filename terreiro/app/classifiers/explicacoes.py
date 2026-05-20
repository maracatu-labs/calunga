"""Templates humanos de títulos, motivos e critérios dos classificadores
do Gonguê.

Cada classificador tem três peças:

- TITULO: frase narrativa com placeholders, usada como título do evento no feed.
- MOTIVO: explicação curta em linguagem humana do por que aquilo é suspeito.
- CRITERIOS: lista de regras objetivas aplicadas pelo classificador.

Os placeholders são preenchidos com `str.format(**contexto)`. Contexto típico:
    parlamentar, partido, uf, valor (str formatada), fornecedor, categoria_despesa,
    orgao_sancionador, tipo_sancao, data
"""

from __future__ import annotations

TITULOS: dict[str, str] = {
    "cnpj_cpf_invalido": (
        "{parlamentar} apresentou nota com CNPJ/CPF inválido no valor de {valor}"
    ),
    "limite_subcota_mensal": (
        "{parlamentar} ({partido}/{uf}) ultrapassou o limite mensal da cota parlamentar"
    ),
    "empresa_irregular": (
        "{parlamentar} pagou {valor} a fornecedor sancionado pelo {orgao_sancionador}"
    ),
    "despesa_eleitoral": (
        "{parlamentar} usou a cota parlamentar em fornecedor de natureza eleitoral"
    ),
    "despesa_fim_de_semana": (
        "{parlamentar} registrou despesa de {valor} em fim de semana ou feriado"
    ),
    "preco_refeicao_anomalo": (
        "{parlamentar} pagou {valor} em uma única refeição bem acima da média"
    ),
}

MOTIVOS_HUMANOS: dict[str, str] = {
    "cnpj_cpf_invalido": (
        "O documento informado na nota não é um CNPJ ou CPF válido pelas regras da Receita Federal. "
        "Isso impede qualquer verificação do fornecedor e pode indicar fraude documental."
    ),
    "limite_subcota_mensal": (
        "A Cota para Exercício da Atividade Parlamentar (CEAP) tem um teto mensal por deputado. "
        "Gastos acima do teto sinalizam que a prestação de contas precisa ser revisada pela Câmara."
    ),
    "empresa_irregular": (
        "Essa empresa aparece em listas oficiais de sanção como CEIS, CNEP ou CEPIM. "
        "Mesmo assim, recebeu pagamento com dinheiro público via cota parlamentar."
    ),
    "despesa_eleitoral": (
        "A cota parlamentar não pode ser usada para atividades eleitorais. "
        "O fornecedor escolhido tem CNAE compatível com serviços de campanha, o que sugere desvio de finalidade."
    ),
    "despesa_fim_de_semana": (
        "Despesas de gabinete registradas em fins de semana ou feriados costumam ser atípicas. "
        "Não são proibidas, mas merecem atenção porque fogem do expediente normal da atividade parlamentar."
    ),
    "preco_refeicao_anomalo": (
        "Esse valor de refeição está bem acima da média dos demais deputados na mesma cidade. "
        "Valores destoantes são sinalizados pelo classificador estatístico e demandam explicação."
    ),
}

CRITERIOS: dict[str, list[str]] = {
    "cnpj_cpf_invalido": [
        "Verifica dígitos verificadores do CNPJ pelo algoritmo oficial.",
        "Verifica dígitos verificadores do CPF quando o documento tem 11 dígitos.",
    ],
    "limite_subcota_mensal": [
        "Soma os gastos mensais do deputado por subcategoria.",
        "Compara com o teto mensal definido pela Câmara para cada tipo de gasto.",
    ],
    "empresa_irregular": [
        "Cruza o CNPJ da nota com as listas CEIS, CNEP e CEPIM do Portal da Transparência.",
        "Verifica se a sanção estava vigente na data da despesa.",
    ],
    "despesa_eleitoral": [
        "Checa o CNAE principal do fornecedor contra uma lista de atividades típicas de campanha.",
        "Considera também razão social contendo termos como gráfica, marketing político ou pesquisa eleitoral.",
    ],
    "despesa_fim_de_semana": [
        "Verifica se a data de emissão da nota cai em sábado, domingo ou feriado nacional.",
    ],
    "preco_refeicao_anomalo": [
        "Agrupa despesas de alimentação por município e calcula estatísticas com K-Means.",
        "Sinaliza valores que ficam muito distantes do centro do cluster da região.",
    ],
}

def gerar_titulo_narrativo(classificador: str, contexto: dict) -> str:
    """Preenche o template de título com os dados reais. Cai pra descrição
    genérica se faltar placeholder.
    """
    template = TITULOS.get(classificador)
    if not template:
        return "Despesa com indício de irregularidade"
    try:
        return template.format(**{k: (v if v is not None else "") for k, v in contexto.items()})
    except (KeyError, IndexError):
        return "Despesa com indício de irregularidade"

def motivo_humano(classificador: str) -> str:
    return MOTIVOS_HUMANOS.get(
        classificador,
        "Despesa sinalizada por um dos classificadores do Gonguê.",
    )

def criterios(classificador: str) -> list[str]:
    return list(CRITERIOS.get(classificador, []))
