import json
from decimal import Decimal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.database import get_pool
from app.queries import despesas as despesas_q
from app.queries import empresas as empresas_q
from app.queries import parlamentares as parlamentares_q
from app.queries import suspeitas as suspeitas_q
from app.services.brasil_api import consultar_cnpj


class BuscarDespesasInput(BaseModel):
    """Busca despesas (gastos) de deputados federais usando dados do CEAP."""

    nome: str | None = Field(None, description="Nome ou parte do nome do deputado")
    deputado_id: int | None = Field(None, description="ID interno do deputado no banco de dados")
    ano: int | None = Field(None, description="Ano das despesas (ex: 2025)")
    mes: int | None = Field(None, description="Mês das despesas (1-12)")
    categoria: str | None = Field(None, description="Categoria da despesa (ex: Alimentação, Combustíveis)")

def _fmt(val: Decimal | None) -> str:
    if val is None:
        return "N/A"
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def _link_parlamentar(nome: str | None, id_externo: str | None, tipo: str | None) -> str:
    """Retorna o nome do parlamentar como hyperlink Markdown para o perfil oficial."""
    if not nome:
        return "N/A"
    if not id_externo or not tipo:
        return nome
    if tipo == "deputado":
        dep_id = id_externo.removeprefix("camara-")
        url = f"https://www.camara.leg.br/deputados/{dep_id}"
    elif tipo == "senador":
        sen_id = id_externo.removeprefix("senado-")
        url = f"https://www25.senado.leg.br/web/senadores/senador/-/perfil/{sen_id}"
    else:
        return nome
    return f"[{nome}]({url})"

def _link_cnpj(cnpj: str | None) -> str | None:
    """Retorna o CNPJ como hyperlink Markdown para busca no Google."""
    if not cnpj:
        return None
    digits = "".join(ch for ch in str(cnpj) if ch.isdigit())
    if not digits:
        return None
    if len(digits) == 14:
        formatado = f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"
    else:
        formatado = digits
    from urllib.parse import quote
    return f"[{formatado}](https://www.google.com/search?q={quote(formatado)})"

_ALIAS_ORGAO_CACHE: dict[str, str] | None = None

async def _carregar_aliases_orgaos() -> dict[str, str]:
    """Carrega sob demanda o mapa lowercase(alias|nome) -> codigo.

    O cache e por processo; nao invalida em runtime — para atualizar os
    aliases em producao, reinicie o worker (ou adicione invalidacao
    explicita quando isso se tornar problema). Degrada para dict vazio se
    a tabela nao existir ou o banco estiver fora.
    """
    global _ALIAS_ORGAO_CACHE
    if _ALIAS_ORGAO_CACHE is not None:
        return _ALIAS_ORGAO_CACHE
    try:
        pool = get_pool()
        rows = await pool.fetch(
            "SELECT codigo, nome_oficial, aliases FROM orgaos_federais WHERE ativo"
        )
        cache: dict[str, str] = {}
        for r in rows:
            cache[r["nome_oficial"].lower()] = r["codigo"]
            for alias in (r["aliases"] or []):
                cache[alias.lower()] = r["codigo"]
        _ALIAS_ORGAO_CACHE = cache
    except Exception:
        _ALIAS_ORGAO_CACHE = {}
    return _ALIAS_ORGAO_CACHE

async def _filtro_orgao(params: list, orgao: str) -> str:
    """Constrói cláusula SQL de filtro por órgão federal.

    Resolução em 3 camadas, a primeira que casar decide a cláusula:
    1. Valor todo numérico -> match exato em `orgao_codigo`.
    2. Valor textual conhecido na tabela orgaos_federais (nome oficial ou
       qualquer alias) -> match exato em `orgao_codigo` pelo código SIORG.
    3. Fallback: ILIKE textual em `orgao_nome`.

    A camada 2 resolve sinônimos populares (ex: "Planalto" -> 20000,
    "MEC" -> 26000) que o ILIKE puro nao achava. Muta `params` in-place.
    """
    valor = orgao.strip()
    if valor.isdigit():
        params.append(valor)
        return f"orgao_codigo = ${len(params)}"

    aliases = await _carregar_aliases_orgaos()
    codigo = aliases.get(valor.lower())
    if codigo:
        params.append(codigo)
        return f"orgao_codigo = ${len(params)}"

    params.append(f"%{valor}%")
    return f"orgao_nome ILIKE ${len(params)}"

def _filtros_limpos(filtros: dict) -> dict:
    """Remove chaves com valor None/vazio para nao poluir o retorno."""
    return {k: v for k, v in filtros.items() if v not in (None, "")}

def _resposta_vazia(aviso: str, fonte: str, filtros: dict | None = None) -> str:
    """Resposta estruturada quando a tool nao encontrou resultados.

    O LLM detecta `modo=vazio` e explica ao usuario o motivo com base em
    `aviso` + `filtros`, em vez de receber uma string solta.
    """
    payload: dict = {"modo": "vazio", "aviso": aviso, "fonte": fonte}
    if filtros:
        payload["filtros"] = _filtros_limpos(filtros)
    return json.dumps(payload, ensure_ascii=False)

def _resposta_erro(mensagem: str, fonte: str) -> str:
    """Resposta estruturada quando a tool recebeu input invalido."""
    return json.dumps({"modo": "erro", "erro": mensagem, "fonte": fonte}, ensure_ascii=False)

_AGRUPAMENTO_CPGF = {
    "orgao": ("orgao_nome", "órgão"),
    "portador": ("portador_nome", "portador"),
    "favorecido": ("favorecido_nome", "favorecido"),
}
_AGRUPAMENTO_CONTRATOS = {
    "orgao": ("orgao_nome", "órgão"),
    "fornecedor": ("fornecedor_nome", "fornecedor"),
}
_AGRUPAMENTO_VIAGENS = {
    "orgao": ("orgao_nome", "órgão"),
    "viajante": ("viajante_nome", "viajante"),
    "destino": ("destino", "destino"),
}
_AGRUPAMENTO_EMENDAS = {
    "autor": ("autor", "autor"),
    "localidade": ("localidade_gasto", "localidade"),
    "tipo": ("tipo_emenda", "tipo"),
    "funcao": ("funcao", "função"),
}

@tool(args_schema=BuscarDespesasInput)
async def buscar_despesas(
    nome: str | None = None,
    deputado_id: int | None = None,
    ano: int | None = None,
    mes: int | None = None,
    categoria: str | None = None,
) -> str:
    """Busca despesas (gastos) de parlamentares. Use para responder perguntas sobre quanto um deputado ou senador gastou."""
    pool = get_pool()

    fonte = "CEAP, Câmara dos Deputados / Senado Federal (dados abertos)"
    filtros = {"nome": nome, "deputado_id": deputado_id, "ano": ano, "mes": mes, "categoria": categoria}

    resumo = await despesas_q.resumo_despesas(
        pool, nome=nome, parlamentar_id=deputado_id, ano=ano, mes=mes, categoria=categoria
    )

    if not resumo:
        return _resposta_vazia("Nenhuma despesa encontrada com os filtros informados.", fonte, filtros)

    return json.dumps({
        "modo": "resumo",
        "parlamentar": resumo["nome"],
        "tipo": resumo["tipo"],
        "partido": resumo["partido"],
        "uf": resumo["uf"],
        "total_despesas": resumo["total_registros"],
        "valor_total": _fmt(resumo["valor_total"]),
        "por_categoria": {
            c["categoria"]: _fmt(c["valor"]) for c in resumo["categorias"]
        },
        "por_mes": {
            m["mes"]: _fmt(m["valor"]) for m in resumo["meses"]
        },
        "maiores_despesas": [
            {
                "fornecedor": t["fornecedor"],
                "categoria": t["categoria"],
                "valor": _fmt(t["valor_liquido"]),
                "data": str(t["data_emissao"]) if t["data_emissao"] else "N/A",
            }
            for t in resumo["top5"]
        ],
        "filtros": _filtros_limpos(filtros),
        "fonte": fonte,
    }, ensure_ascii=False)

class RankingDespesasInput(BaseModel):
    """Ranking dos parlamentares (deputados e senadores) que mais gastaram."""

    tipo: str | None = Field(None, description="Tipo: 'deputado' ou 'senador'. Se omitido, lista ambos.")
    ano: int | None = Field(None, description="Ano (ex: 2024)")
    categoria: str | None = Field(None, description="Categoria da despesa (ex: Alimentação, Combustíveis)")
    uf: str | None = Field(None, description="Sigla do estado (ex: SP, MG)")
    partido: str | None = Field(None, description="Sigla do partido (ex: PL, PT)")

@tool(args_schema=RankingDespesasInput)
async def ranking_despesas(
    tipo: str | None = None,
    ano: int | None = None,
    categoria: str | None = None,
    uf: str | None = None,
    partido: str | None = None,
) -> str:
    """Ranking dos parlamentares que mais gastaram. Use para comparar gastos entre parlamentares ou responder 'quem mais gastou'. Filtre por tipo='senador' para senadores ou tipo='deputado' para deputados."""
    pool = get_pool()

    fonte = "CEAP, Câmara dos Deputados / Senado Federal (dados abertos)"
    filtros = {"tipo": tipo, "ano": ano, "categoria": categoria, "uf": uf, "partido": partido}

    rows = await despesas_q.ranking_deputados_por_gasto(
        pool, tipo=tipo, ano=ano, categoria=categoria, uf=uf, partido=partido, limit=10
    )

    if not rows:
        return _resposta_vazia("Nenhum parlamentar encontrado com os filtros informados.", fonte, filtros)

    ranking = []
    for i, r in enumerate(rows, 1):
        valor = r["valor_total"] or Decimal("0")
        ranking.append({
            "posicao": i,
            "parlamentar": r["nome"],
            "tipo": r["tipo"],
            "partido": r["partido"],
            "uf": r["uf"],
            "total_despesas": r["total_registros"],
            "valor_total": f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        })

    return json.dumps({
        "modo": "ranking",
        "campo": "parlamentar",
        "ranking": ranking,
        "filtros": _filtros_limpos(filtros),
        "fonte": fonte,
    }, ensure_ascii=False)

class ListarParlamentaresInput(BaseModel):
    """Lista parlamentares (deputados e/ou senadores) em exercício."""

    tipo: str | None = Field(None, description="Tipo: 'deputado' ou 'senador'. Se omitido, lista ambos.")
    uf: str | None = Field(None, description="Sigla do estado (ex: SP, RJ, MG)")
    partido: str | None = Field(None, description="Sigla do partido (ex: PT, PL, PSOL)")
    nome: str | None = Field(None, description="Nome ou parte do nome do parlamentar")

@tool(args_schema=ListarParlamentaresInput)
async def listar_parlamentares(
    tipo: str | None = None,
    uf: str | None = None,
    partido: str | None = None,
    nome: str | None = None,
) -> str:
    """Lista parlamentares (deputados e senadores). Use para encontrar parlamentares por tipo, estado, partido ou nome."""
    pool = get_pool()

    fonte = "Câmara dos Deputados + Senado Federal (dados abertos)"
    filtros = {"tipo": tipo, "uf": uf, "partido": partido, "nome": nome}

    rows = await parlamentares_q.listar_parlamentares(
        pool, tipo=tipo, uf=uf, partido=partido, nome=nome, limit=30
    )

    if not rows:
        return _resposta_vazia("Nenhum parlamentar encontrado com os filtros informados.", fonte, filtros)

    parlamentares = [
        {
            "id": r["id"],
            "nome": r["nome"],
            "tipo": r["tipo"],
            "partido": r["partido"],
            "uf": r["uf"],
        }
        for r in rows
    ]

    return json.dumps({
        "modo": "lista",
        "parlamentares": parlamentares,
        "total_registros": len(parlamentares),
        "filtros": _filtros_limpos(filtros),
        "fonte": fonte,
    }, ensure_ascii=False)

class ListarExecutivosInput(BaseModel):
    """Lista chefes do poder executivo: governadores dos 27 estados, prefeitos das 27 capitais e presidente da República."""

    cargo: str | None = Field(
        None,
        description="Cargo: 'governador', 'prefeito' ou 'presidente'. Se omitido, lista todos os três tipos.",
    )
    uf: str | None = Field(None, description="Sigla do estado (ex: SP, RJ, BA). Relevante para governadores e prefeitos.")
    partido: str | None = Field(None, description="Sigla do partido (ex: PT, PL, PSD)")
    nome: str | None = Field(None, description="Nome ou parte do nome do executivo")

_CARGOS_EXECUTIVOS = {"governador", "prefeito", "presidente"}

@tool(args_schema=ListarExecutivosInput)
async def listar_executivos(
    cargo: str | None = None,
    uf: str | None = None,
    partido: str | None = None,
    nome: str | None = None,
) -> str:
    """Lista chefes do poder executivo: governadores dos 27 estados, prefeitos das 27 capitais e presidente da República. Use para responder 'quem é o governador de SP', 'quem é o prefeito de Recife', 'quais governadores são do PL', 'qual o partido do presidente'. Cobertura: apenas governadores estaduais e prefeitos das capitais (não cobre prefeitos de cidades do interior). Dados vêm do TSE (eleições 2022 para governadores, 2024 para prefeitos de capitais)."""
    pool = get_pool()

    query = """
        SELECT p.id, p.nome, p.tipo, p.partido, p.uf, p.situacao,
               e.nome AS ente_nome, e.tipo AS ente_tipo
        FROM parlamentares p
        LEFT JOIN entes e ON e.id = p.ente_id
        WHERE 1=1
    """
    params: list = []

    fonte = "TSE, Eleições 2022 e 2024 (dados abertos)"
    filtros = {"cargo": cargo, "uf": uf, "partido": partido, "nome": nome}

    if cargo:
        cargo_norm = cargo.lower().strip()
        if cargo_norm not in _CARGOS_EXECUTIVOS:
            return _resposta_erro(
                f"cargo='{cargo}' inválido. Use um de: {sorted(_CARGOS_EXECUTIVOS)}",
                fonte,
            )
        params.append(cargo_norm)
        query += f" AND p.tipo = ${len(params)}"
    else:
        query += " AND p.tipo IN ('governador', 'prefeito', 'presidente')"

    if uf:
        params.append(uf.upper())
        query += f" AND p.uf = ${len(params)}"

    if partido:
        params.append(partido.upper())
        query += f" AND p.partido = ${len(params)}"

    if nome:
        params.append(f"%{nome}%")
        query += f" AND p.nome ILIKE ${len(params)}"

    query += " ORDER BY p.tipo, p.uf, p.nome LIMIT 30"

    rows = await pool.fetch(query, *params)

    if not rows:
        return _resposta_vazia("Nenhum executivo encontrado com os filtros informados.", fonte, filtros)

    executivos = [
        {
            "id": r["id"],
            "cargo": r["tipo"],
            "nome": r["nome"],
            "partido": r["partido"],
            "uf": r["uf"],
            "ente": r["ente_nome"] or "N/A",
            "situacao": r["situacao"] or "N/A",
        }
        for r in rows
    ]

    return json.dumps({
        "modo": "lista",
        "executivos": executivos,
        "total_registros": len(executivos),
        "filtros": _filtros_limpos(filtros),
        "fonte": fonte,
    }, ensure_ascii=False)

class BuscarSuspeitasInput(BaseModel):
    """Busca despesas sinalizadas como suspeitas pelos classificadores."""

    nome: str | None = Field(None, description="Nome do parlamentar")
    classificador: str | None = Field(None, description="Tipo: 'cnpj_cpf_invalido' ou 'limite_subcota_mensal'")
    ano: int | None = Field(None, description="Ano (ex: 2024)")

@tool(args_schema=BuscarSuspeitasInput)
async def buscar_suspeitas(
    nome: str | None = None,
    classificador: str | None = None,
    ano: int | None = None,
) -> str:
    """Busca despesas sinalizadas como suspeitas. Use para responder sobre irregularidades ou anomalias detectadas."""
    pool = get_pool()

    fonte = "Classificadores do Gonguê (Maracatu)"
    filtros = {"nome": nome, "classificador": classificador, "ano": ano}

    rows = await suspeitas_q.listar_suspeitas(
        pool, parlamentar_nome=nome, classificador=classificador, ano=ano, limit=20
    )

    if not rows:
        return _resposta_vazia("Nenhuma suspeita encontrada com os filtros informados.", fonte, filtros)

    suspeitas = []
    for r in rows:
        suspeitas.append({
            "despesa_id": r["despesa_id"],
            "parlamentar": _link_parlamentar(r["parlamentar_nome"], r["parlamentar_id_externo"], r["parlamentar_tipo"]),
            "partido": r["partido"],
            "uf": r["uf"],
            "classificador": r["classificador"],
            "categoria": r["categoria"],
            "fornecedor": r["fornecedor"],
            "cnpj_cpf": _link_cnpj(r["cnpj_cpf"]) or r["cnpj_cpf"],
            "valor": _fmt(r["valor_liquido"]),
            "ano": r["ano"],
            "mes": r["mes"],
            "motivo": (json.loads(r["detalhes"]) if isinstance(r["detalhes"], str) else r["detalhes"] or {}).get("motivo", ""),
        })

    stats = await suspeitas_q.contar_suspeitas_por_classificador(pool)
    totais_por_classificador = {r["classificador"]: r["total"] for r in stats}

    return json.dumps({
        "modo": "lista",
        "suspeitas": suspeitas,
        "total_registros": len(suspeitas),
        "totais_por_classificador": totais_por_classificador,
        "filtros": _filtros_limpos(filtros),
        "fonte": fonte,
    }, ensure_ascii=False)

class ConsultarReciboInput(BaseModel):
    """Consulta a análise OCR + LLM do recibo de uma despesa CEAP específica."""

    despesa_id: int = Field(description="ID interno da despesa no banco (coluna despesas.id). Use o valor retornado por buscar_suspeitas ou buscar_despesas.")

@tool(args_schema=ConsultarReciboInput)
async def consultar_recibo(despesa_id: int) -> str:
    """Retorna a análise detalhada do recibo de uma despesa CEAP (via OCR + LLM). Útil quando o usuário quer saber o que foi comprado, se havia álcool, ou por que um gasto foi sinalizado como irregular. Só funciona em despesas de alimentação; se não houver análise, avise o usuário. Use o despesa_id retornado por buscar_suspeitas ou buscar_despesas."""
    pool = get_pool()

    query = """
        SELECT s.detalhes, s.probabilidade,
               d.fornecedor, d.cnpj_cpf, d.valor_liquido, d.data_emissao,
               d.categoria, d.url_documento,
               p.nome AS parlamentar_nome, p.partido, p.uf,
               p.id_externo AS parlamentar_id_externo, p.tipo AS parlamentar_tipo
        FROM suspeitas s
        JOIN despesas d ON d.id = s.despesa_id
        JOIN parlamentares p ON p.id = d.parlamentar_id
        WHERE s.despesa_id = $1 AND s.classificador = 'ocr_recibo'
        LIMIT 1
    """
    fonte = "OCR + análise LLM de recibo CEAP (Maracatu)"
    row = await pool.fetchrow(query, despesa_id)

    if not row:
        return _resposta_vazia(
            f"Nenhuma análise de recibo disponível para a despesa {despesa_id}. "
            "O OCR roda apenas em despesas de alimentação com indícios de irregularidade.",
            fonte,
            {"despesa_id": despesa_id},
        )

    detalhes_raw = row["detalhes"]
    detalhes = (
        json.loads(detalhes_raw) if isinstance(detalhes_raw, str) else (detalhes_raw or {})
    )

    itens_raw = detalhes.get("itens") or []
    itens: list[dict] = []
    for item in itens_raw:
        if not isinstance(item, dict):
            continue
        itens.append({
            "descricao": item.get("descricao"),
            "quantidade": item.get("quantidade"),
            "valor": item.get("valor"),
        })

    analise = {
        "itens": itens,
        "valor_total_calculado": detalhes.get("valor_total"),
        "tem_alcool": detalhes.get("tem_alcool"),
        "itens_discriminados": detalhes.get("itens_discriminados"),
        "irregularidades": detalhes.get("irregularidades") or [],
    }

    return json.dumps({
        "modo": "item",
        "despesa_id": despesa_id,
        "parlamentar": _link_parlamentar(
            row["parlamentar_nome"],
            row["parlamentar_id_externo"],
            row["parlamentar_tipo"],
        ),
        "partido": row["partido"],
        "uf": row["uf"],
        "fornecedor": row["fornecedor"],
        "cnpj_cpf": _link_cnpj(row["cnpj_cpf"]) or row["cnpj_cpf"],
        "valor_declarado": _fmt(row["valor_liquido"]),
        "data": str(row["data_emissao"]) if row["data_emissao"] else "N/A",
        "categoria": row["categoria"],
        "url_recibo": row["url_documento"],
        "analise": analise,
        "fonte": fonte,
    }, ensure_ascii=False)

class BuscarEmpresaInput(BaseModel):
    """Busca dados cadastrais de uma empresa por CNPJ."""

    cnpj: str = Field(description="CNPJ da empresa (ex: 06266344000557 ou 06.266.344/0005-57)")

@tool(args_schema=BuscarEmpresaInput)
async def buscar_empresa(cnpj: str) -> str:
    """Busca dados de uma empresa por CNPJ. Retorna razão social, situação cadastral, CNAE, endereço e sanções."""
    pool = get_pool()
    fonte = "Receita Federal (bulk) / BrasilAPI / Portal da Transparência"

    row = await empresas_q.buscar_empresa_por_cnpj(pool, cnpj)

    if not row:

        data = await consultar_cnpj(cnpj, pool=pool)
        if not data:
            return _resposta_vazia(
                f"CNPJ {cnpj} não encontrado na base de dados nem na BrasilAPI.",
                fonte,
                {"cnpj": cnpj},
            )
        result = data
    else:
        result = {
            "cnpj": row["cnpj"],
            "razao_social": row["razao_social"],
            "nome_fantasia": row["nome_fantasia"],
            "situacao_cadastral": row["situacao_cadastral"],
            "data_situacao": str(row["data_situacao"]) if row["data_situacao"] else None,
            "natureza_juridica": row["natureza_juridica"],
            "atividade_principal": row["atividade_principal_codigo"],
            "logradouro": row["logradouro"],
            "municipio": row["municipio"],
            "uf": row["uf"],
            "cep": row["cep"],
            "capital_social": str(row["capital_social"]) if row["capital_social"] else None,
            "porte": row["porte"],
            "data_abertura": str(row["data_abertura"]) if row["data_abertura"] else None,
        }

    sancoes = await empresas_q.empresa_tem_sancao(pool, cnpj)
    if sancoes:
        result["sancoes"] = [
            {"tipo": s["tipo"], "orgao": s["orgao_sancionador"], "inicio": str(s["data_inicio"]) if s["data_inicio"] else None}
            for s in sancoes
        ]
        result["alerta"] = f"Empresa possui {len(sancoes)} sanção(ões) ativa(s)."

        from app.schemas.feed import Ator, Contexto, Objeto, Severidade
        from app.services.feed import publicar_descoberta_chat
        from app.services.feed_enrichment import (
            construir_dados_ricos,
            formatar_cnpj,
            link_busca_cnpj,
            link_portal_transparencia_sancao,
        )

        razao = result.get("razao_social") or cnpj
        tipos_sancao = sorted({s["tipo"] for s in sancoes})
        tipos_str = ", ".join(tipos_sancao)
        cnpj_digits = "".join(ch for ch in str(cnpj) if ch.isdigit())

        titulo = f"Empresa {razao} está na lista {tipos_str} do Portal da Transparência"
        descricao = (
            f"Verificação solicitada por cidadão via chat. A empresa {razao}"
            f" (CNPJ {formatar_cnpj(cnpj_digits) or cnpj}) aparece em {len(sancoes)} sanção(ões)"
            f" nas listas {tipos_str}. Empresas nessas listas estão impedidas de contratar"
            " com a administração pública durante a vigência da penalidade."
        )

        ator = Ator(nome="Cidadão investigando no chat", papel="Descoberta cidadã")
        objeto = Objeto(
            tipo="empresa",
            nome=razao,
            identificador=cnpj_digits,
            identificador_formatado=formatar_cnpj(cnpj_digits),
            detalhes={
                "situacao_cadastral": result.get("situacao_cadastral"),
                "atividade_principal": result.get("atividade_principal"),
                "municipio": result.get("municipio"),
                "uf": result.get("uf"),
                "sancoes": [
                    {
                        "tipo": s["tipo"],
                        "orgao": s["orgao_sancionador"],
                        "inicio": str(s["data_inicio"]) if s["data_inicio"] else None,
                    }
                    for s in sancoes
                ],
            },
        )
        contexto = Contexto(alertas=[
            f"{len(sancoes)} sanção(ões) registrada(s) nas listas {tipos_str}.",
        ])
        links = [link_busca_cnpj(cnpj_digits)]
        for tipo_sancao in tipos_sancao:
            links.append(link_portal_transparencia_sancao(tipo_sancao))

        dados_ricos = construir_dados_ricos(
            ator=ator,
            objeto=objeto,
            contexto=contexto,
            links=links,
            severidade=Severidade.CRITICO,
        )

        await publicar_descoberta_chat(
            tipo="empresa_sancionada",
            categoria="irregularidade",
            titulo=titulo,
            descricao=descricao,
            dados=dados_ricos,
            referencia_tipo="empresa",
            referencia_id=None,
            relevancia=0.9,
        )

    result["modo"] = "item"
    result["fonte"] = fonte
    return json.dumps(result, ensure_ascii=False)

class BuscarSimilarInput(BaseModel):
    """Busca em todas as bases por texto livre (busca semântica)."""

    texto: str = Field(description="Texto de busca livre (ex: 'reforma tributária', 'contrato de limpeza hospitalar', 'emenda para saneamento')")

@tool(args_schema=BuscarSimilarInput)
async def buscar_similar(texto: str) -> str:
    """Busca por texto livre usando busca semântica em TODAS as bases: despesas, contratos, licitações, emendas, votações, proposições, viagens, cartão corporativo (CPGF) e sanções. Use quando o usuário faz uma pergunta genérica ou quer encontrar algo sem saber exatamente onde está."""
    from app.queries.busca_semantica import busca_universal
    from app.services.embeddings import generate_embedding

    pool = get_pool()
    fonte = "Busca semântica multi-base (Maracatu)"

    embedding = await generate_embedding(texto)
    results = await busca_universal(pool, texto, embedding, limit=10)

    if not results:
        return _resposta_vazia("Nenhum resultado encontrado para essa busca.", fonte, {"texto": texto})

    return json.dumps({
        "modo": "lista",
        "resultados": results,
        "total_registros": len(results),
        "query": texto,
        "fonte": fonte,
    }, ensure_ascii=False)

class ExplicarTermoInput(BaseModel):
    """Consulta o glossário de termos orçamentários, fiscais e de transparência do Maracatu."""

    termo: str = Field(description="Nome ou sinônimo do termo (ex: 'LOA', 'Emenda Pix', 'orçamento secreto', 'cota parlamentar')")

@tool(args_schema=ExplicarTermoInput)
async def explicar_termo(termo: str) -> str:
    """Consulta o glossário de termos orçamentários, fiscais e de transparência do Maracatu. Use quando o usuário perguntar 'o que é X' sobre conceitos como LOA, LDO, PPA, RCL, CEAP, CPGF, Emenda Pix, Empenho, Liquidação, CEIS, CNEP, RREO, RGF, SICONFI, etc. Aceita sinônimos ('cartão corporativo' acha CPGF, 'cota parlamentar' acha CEAP, 'orçamento secreto' acha Emenda de Relator). Sempre prefira essa tool a responder de memória em perguntas conceituais. As definições aqui vêm de fontes oficiais (Tesouro, Câmara, Senado) e trazem URL de referência."""
    pool = get_pool()
    fonte = "Glossário Maracatu (fontes oficiais)"

    termo_limpo = (termo or "").strip()
    if not termo_limpo:
        return _resposta_vazia(
            "Nenhum termo informado. Passe o nome do conceito que o usuário quer entender.",
            fonte,
            {"termo": termo},
        )

    row = await pool.fetchrow(
        """
        SELECT termo, aliases, categoria, definicao, fonte_url
        FROM glossario_termos
        WHERE LOWER(termo) = LOWER($1)
        """,
        termo_limpo,
    )

    if row is None:
        row = await pool.fetchrow(
            """
            SELECT termo, aliases, categoria, definicao, fonte_url
            FROM glossario_termos
            WHERE EXISTS (
                SELECT 1 FROM unnest(aliases) a WHERE LOWER(a) = LOWER($1)
            )
            """,
            termo_limpo,
        )

    if row is None:
        row = await pool.fetchrow(
            """
            SELECT termo, aliases, categoria, definicao, fonte_url
            FROM glossario_termos
            WHERE termo ILIKE $1 OR EXISTS (
                SELECT 1 FROM unnest(aliases) a WHERE a ILIKE $1
            )
            LIMIT 1
            """,
            f"%{termo_limpo}%",
        )

    if row is None:
        return _resposta_vazia(
            (
                f"O termo '{termo_limpo}' não está no glossário do Maracatu. "
                "Se for responder com conhecimento geral, avise que a definição não vem "
                "do glossário oficial e cite fonte externa com cautela."
            ),
            fonte,
            {"termo": termo_limpo},
        )

    return json.dumps({
        "modo": "item",
        "termo": row["termo"],
        "aliases": list(row["aliases"] or []),
        "categoria": row["categoria"],
        "definicao": row["definicao"],
        "fonte_url": row["fonte_url"],
        "filtros": _filtros_limpos({"termo": termo_limpo}),
        "fonte": fonte,
    }, ensure_ascii=False)

class BuscarCPGFInput(BaseModel):
    """Busca gastos do cartão corporativo do governo federal (CPGF)."""

    orgao: str | None = Field(None, description="Nome ou código do órgão (ex: 'Presidência', '20000')")
    ano: int | None = Field(None, description="Ano (ex: 2025)")
    mes: int | None = Field(None, description="Mês (1-12)")
    portador: str | None = Field(None, description="Nome do portador do cartão")
    agrupar_por: str | None = Field(
        None,
        description="Agrupa os resultados em ranking. Valores: 'orgao' (quais órgãos mais gastaram), 'portador' (quais portadores mais gastaram), 'favorecido' (maiores favorecidos). Se omitido, retorna lista de transações individuais.",
    )

@tool(args_schema=BuscarCPGFInput)
async def buscar_cpgf(
    orgao: str | None = None,
    ano: int | None = None,
    mes: int | None = None,
    portador: str | None = None,
    agrupar_por: str | None = None,
) -> str:
    """Busca gastos do cartão corporativo (CPGF) do governo federal. Use para perguntas sobre cartão corporativo, gastos do Planalto, da Presidência ou de ministérios. Para rankings do tipo "quais órgãos/portadores mais gastaram", use agrupar_por."""
    pool = get_pool()

    params: list = []
    where: list[str] = []
    if orgao:
        where.append(await _filtro_orgao(params, orgao))
    if ano:
        params.append(ano)
        where.append(f"ano_extrato = ${len(params)}")
    if mes:
        params.append(mes)
        where.append(f"mes_extrato = ${len(params)}")
    if portador:
        params.append(f"%{portador}%")
        where.append(f"portador_nome ILIKE ${len(params)}")

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    filtros_aplicados = _filtros_limpos({"orgao": orgao, "ano": ano, "mes": mes, "portador": portador})
    fonte = "CPGF, Portal da Transparência (dados abertos)"
    aviso_vazio = "Nenhum gasto CPGF encontrado com os filtros informados."

    if agrupar_por:
        if agrupar_por not in _AGRUPAMENTO_CPGF:
            return _resposta_erro(
                f"agrupar_por='{agrupar_por}' inválido. Use um de: {list(_AGRUPAMENTO_CPGF)}",
                fonte,
            )
        campo_sql, campo_rotulo = _AGRUPAMENTO_CPGF[agrupar_por]
        query = f"""
            SELECT {campo_sql} AS nome,
                   COUNT(*) AS qtde,
                   SUM(valor) AS valor_total
            FROM cpgf {where_sql}
            GROUP BY {campo_sql}
            ORDER BY valor_total DESC NULLS LAST
            LIMIT 20
        """
        rows = await pool.fetch(query, *params)
        if not rows:
            return _resposta_vazia(aviso_vazio, fonte, filtros_aplicados)
        return json.dumps({
            "modo": "ranking",
            "campo": campo_rotulo,
            "ranking": [
                {
                    "nome": r["nome"] or "N/A",
                    "quantidade": r["qtde"],
                    "valor_total": _fmt(r["valor_total"]),
                }
                for r in rows
            ],
            "filtros": filtros_aplicados,
            "fonte": fonte,
        }, ensure_ascii=False)

    query = f"""
        SELECT orgao_nome, portador_nome, favorecido_nome, transacao, valor,
               data_transacao, mes_extrato, ano_extrato
        FROM cpgf {where_sql}
        ORDER BY valor DESC NULLS LAST LIMIT 20
    """
    rows = await pool.fetch(query, *params)
    if not rows:
        return _resposta_vazia(aviso_vazio, fonte, filtros_aplicados)

    totais_query = f"SELECT COUNT(*) AS total, SUM(valor) AS valor_total FROM cpgf {where_sql}"
    totais = await pool.fetchrow(totais_query, *params)

    gastos = [{
        "orgao": r["orgao_nome"],
        "portador": r["portador_nome"],
        "favorecido": r["favorecido_nome"],
        "transacao": r["transacao"],
        "valor": _fmt(r["valor"]),
        "data": str(r["data_transacao"]) if r["data_transacao"] else "N/A",
    } for r in rows]

    return json.dumps({
        "modo": "lista",
        "gastos": gastos,
        "total_registros": totais["total"] if totais else 0,
        "valor_total": _fmt(totais["valor_total"]) if totais else "N/A",
        "filtros": filtros_aplicados,
        "fonte": fonte,
    }, ensure_ascii=False)

class BuscarContratosInput(BaseModel):
    """Busca contratos do governo federal."""

    orgao: str | None = Field(None, description="Nome ou código do órgão")
    fornecedor: str | None = Field(None, description="Nome do fornecedor")
    cnpj: str | None = Field(None, description="CNPJ do fornecedor")
    agrupar_por: str | None = Field(
        None,
        description="Agrupa em ranking por 'orgao' (quais órgãos mais contrataram) ou 'fornecedor' (maiores contratados). Se omitido, retorna lista de contratos.",
    )

@tool(args_schema=BuscarContratosInput)
async def buscar_contratos(
    orgao: str | None = None,
    fornecedor: str | None = None,
    cnpj: str | None = None,
    agrupar_por: str | None = None,
) -> str:
    """Busca contratos do governo federal. Use para perguntas sobre contratos, fornecedores do governo, licitações ganhas. Para "quais empresas mais recebem" ou "quais órgãos mais contratam", use agrupar_por."""
    pool = get_pool()

    params: list = []
    where: list[str] = []
    if orgao:
        where.append(await _filtro_orgao(params, orgao))
    if fornecedor:
        params.append(f"%{fornecedor}%")
        where.append(f"fornecedor_nome ILIKE ${len(params)}")
    if cnpj:
        from app.sanitize import limpar_documento
        params.append(limpar_documento(cnpj))
        where.append(f"fornecedor_cnpj_cpf = ${len(params)}")

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    filtros_aplicados = _filtros_limpos({"orgao": orgao, "fornecedor": fornecedor, "cnpj": cnpj})
    fonte = "Portal da Transparência, Contratos Federais (dados abertos)"
    aviso_vazio = "Nenhum contrato encontrado com os filtros informados."

    if agrupar_por:
        if agrupar_por not in _AGRUPAMENTO_CONTRATOS:
            return _resposta_erro(
                f"agrupar_por='{agrupar_por}' inválido. Use um de: {list(_AGRUPAMENTO_CONTRATOS)}",
                fonte,
            )
        campo_sql, campo_rotulo = _AGRUPAMENTO_CONTRATOS[agrupar_por]
        query = f"""
            SELECT {campo_sql} AS nome,
                   COUNT(*) AS qtde,
                   SUM(valor_final) AS valor_total
            FROM contratos {where_sql}
            GROUP BY {campo_sql}
            ORDER BY valor_total DESC NULLS LAST
            LIMIT 20
        """
        rows = await pool.fetch(query, *params)
        if not rows:
            return _resposta_vazia(aviso_vazio, fonte, filtros_aplicados)
        return json.dumps({
            "modo": "ranking",
            "campo": campo_rotulo,
            "ranking": [
                {
                    "nome": r["nome"] or "N/A",
                    "quantidade": r["qtde"],
                    "valor_total": _fmt(r["valor_total"]),
                }
                for r in rows
            ],
            "filtros": filtros_aplicados,
            "fonte": fonte,
        }, ensure_ascii=False)

    query = f"""
        SELECT orgao_nome, fornecedor_nome, fornecedor_cnpj_cpf, objeto, numero,
               modalidade_licitacao, situacao, valor_inicial, valor_final,
               data_inicio, data_fim
        FROM contratos {where_sql}
        ORDER BY valor_final DESC NULLS LAST LIMIT 15
    """
    rows = await pool.fetch(query, *params)
    if not rows:
        return _resposta_vazia(aviso_vazio, fonte, filtros_aplicados)

    contratos = [{
        "orgao": r["orgao_nome"],
        "fornecedor": r["fornecedor_nome"],
        "cnpj": r["fornecedor_cnpj_cpf"],
        "objeto": (r["objeto"] or "")[:200],
        "numero": r["numero"],
        "modalidade": r["modalidade_licitacao"],
        "situacao": r["situacao"],
        "valor_inicial": _fmt(r["valor_inicial"]),
        "valor_final": _fmt(r["valor_final"]),
        "vigencia": f"{r['data_inicio']} a {r['data_fim']}" if r["data_inicio"] else "N/A",
    } for r in rows]

    return json.dumps({
        "modo": "lista",
        "contratos": contratos,
        "total_registros": len(contratos),
        "filtros": filtros_aplicados,
        "fonte": fonte,
    }, ensure_ascii=False)

class BuscarViagensInput(BaseModel):
    """Busca viagens a serviço do governo federal."""

    orgao: str | None = Field(None, description="Nome ou código do órgão")
    viajante: str | None = Field(None, description="Nome do viajante")
    ano: int | None = Field(None, description="Ano (ex: 2025)")
    agrupar_por: str | None = Field(
        None,
        description="Agrupa em ranking por 'orgao', 'viajante' ou 'destino'. Soma passagens + diárias. Se omitido, retorna lista de viagens.",
    )

@tool(args_schema=BuscarViagensInput)
async def buscar_viagens(
    orgao: str | None = None,
    viajante: str | None = None,
    ano: int | None = None,
    agrupar_por: str | None = None,
) -> str:
    """Busca viagens a serviço pagas pelo governo federal. Use para perguntas sobre viagens oficiais, diárias, passagens aéreas de servidores. Para rankings do tipo "quais órgãos mais gastaram com viagens" ou "quais servidores mais viajaram", use agrupar_por."""
    pool = get_pool()

    params: list = []
    where: list[str] = []
    if orgao:
        where.append(await _filtro_orgao(params, orgao))
    if viajante:
        params.append(f"%{viajante}%")
        where.append(f"viajante_nome ILIKE ${len(params)}")
    if ano:
        params.append(ano)
        where.append(f"EXTRACT(YEAR FROM data_ida) = ${len(params)}")

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    filtros_aplicados = _filtros_limpos({"orgao": orgao, "viajante": viajante, "ano": ano})
    fonte = "Portal da Transparência, Viagens a Serviço (dados abertos)"
    aviso_vazio = "Nenhuma viagem encontrada com os filtros informados."
    soma_total = "COALESCE(valor_passagens,0) + COALESCE(valor_diarias,0) + COALESCE(valor_outros,0)"

    if agrupar_por:
        if agrupar_por not in _AGRUPAMENTO_VIAGENS:
            return _resposta_erro(
                f"agrupar_por='{agrupar_por}' inválido. Use um de: {list(_AGRUPAMENTO_VIAGENS)}",
                fonte,
            )
        campo_sql, campo_rotulo = _AGRUPAMENTO_VIAGENS[agrupar_por]
        query = f"""
            SELECT {campo_sql} AS nome,
                   COUNT(*) AS qtde,
                   SUM({soma_total}) AS valor_total
            FROM viagens {where_sql}
            GROUP BY {campo_sql}
            ORDER BY valor_total DESC NULLS LAST
            LIMIT 20
        """
        rows = await pool.fetch(query, *params)
        if not rows:
            return _resposta_vazia(aviso_vazio, fonte, filtros_aplicados)
        return json.dumps({
            "modo": "ranking",
            "campo": campo_rotulo,
            "ranking": [
                {
                    "nome": r["nome"] or "N/A",
                    "quantidade": r["qtde"],
                    "valor_total": _fmt(r["valor_total"]),
                }
                for r in rows
            ],
            "filtros": filtros_aplicados,
            "fonte": fonte,
        }, ensure_ascii=False)

    query = f"""
        SELECT orgao_nome, viajante_nome, cargo, destino, motivo, urgente,
               data_ida, data_volta, valor_passagens, valor_diarias, valor_outros
        FROM viagens {where_sql}
        ORDER BY ({soma_total}) DESC NULLS LAST LIMIT 20
    """
    rows = await pool.fetch(query, *params)
    if not rows:
        return _resposta_vazia(aviso_vazio, fonte, filtros_aplicados)

    viagens = [{
        "orgao": r["orgao_nome"],
        "viajante": r["viajante_nome"],
        "cargo": r["cargo"],
        "destino": r["destino"],
        "motivo": (r["motivo"] or "")[:150],
        "urgente": r["urgente"],
        "periodo": f"{r['data_ida']} a {r['data_volta']}" if r["data_ida"] else "N/A",
        "passagens": _fmt(r["valor_passagens"]),
        "diarias": _fmt(r["valor_diarias"]),
    } for r in rows]

    return json.dumps({
        "modo": "lista",
        "viagens": viagens,
        "total_registros": len(viagens),
        "filtros": filtros_aplicados,
        "fonte": fonte,
    }, ensure_ascii=False)

class BuscarEmendasInput(BaseModel):
    """Busca emendas parlamentares e sua execução orçamentária, incluindo emendas Pix."""

    autor: str | None = Field(None, description="Nome do autor (parlamentar ou bancada)")
    ano: int | None = Field(None, description="Ano (ex: 2025)")
    localidade: str | None = Field(None, description="Localidade do gasto (ex: 'São Paulo', 'Nacional')")
    tipo: str | None = Field(None, description="Tipo: 'pix' para Emendas Pix (Transferências Especiais), 'bancada', 'comissao', 'relator' (orçamento secreto), ou None para todas")
    agrupar_por: str | None = Field(
        None,
        description="Agrupa em ranking por 'autor' (quais parlamentares apresentaram mais), 'localidade' (onde mais foi gasto), 'tipo' (distribuição por tipo) ou 'funcao' (área de aplicação). Usa valor_empenhado como métrica. Se omitido, retorna lista de emendas.",
    )

_EMENDAS_TIPO_MAP = {
    "pix": "Emenda Individual - Transferências Especiais",
    "bancada": "Emenda de Bancada",
    "comissao": "Emenda de Comissão",
    "relator": "Emenda de Relator",
    "individual": "Emenda Individual - Transferências com Finalidade Definida",
}

@tool(args_schema=BuscarEmendasInput)
async def buscar_emendas(
    autor: str | None = None,
    ano: int | None = None,
    localidade: str | None = None,
    tipo: str | None = None,
    agrupar_por: str | None = None,
) -> str:
    """Busca emendas parlamentares e sua execução. Inclui emendas Pix (Transferências Especiais: dinheiro enviado direto a estados/municípios sem convênio nem prestação de contas detalhada). Use tipo='pix' para filtrar emendas Pix, tipo='relator' para orçamento secreto. Para rankings do tipo "quais parlamentares apresentaram mais emendas" ou "onde as emendas Pix foram mais direcionadas", use agrupar_por."""
    pool = get_pool()

    params: list = []
    where: list[str] = []
    if tipo:
        tipo_db = _EMENDAS_TIPO_MAP.get(tipo.lower(), tipo)
        params.append(tipo_db)
        where.append(f"tipo_emenda = ${len(params)}")
    if autor:
        params.append(f"%{autor}%")
        where.append(f"autor ILIKE ${len(params)}")
    if ano:
        params.append(ano)
        where.append(f"ano = ${len(params)}")
    if localidade:
        params.append(f"%{localidade}%")
        where.append(f"localidade_gasto ILIKE ${len(params)}")

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    filtros_aplicados = _filtros_limpos({"autor": autor, "ano": ano, "localidade": localidade, "tipo": tipo})
    fonte = "Portal da Transparência, Emendas Parlamentares (dados abertos)"
    aviso_vazio = "Nenhuma emenda encontrada com os filtros informados."

    if agrupar_por:
        if agrupar_por not in _AGRUPAMENTO_EMENDAS:
            return _resposta_erro(
                f"agrupar_por='{agrupar_por}' inválido. Use um de: {list(_AGRUPAMENTO_EMENDAS)}",
                fonte,
            )
        campo_sql, campo_rotulo = _AGRUPAMENTO_EMENDAS[agrupar_por]
        query = f"""
            SELECT {campo_sql} AS nome,
                   COUNT(*) AS qtde,
                   SUM(valor_empenhado) AS valor_empenhado,
                   SUM(valor_pago) AS valor_pago
            FROM emendas {where_sql}
            GROUP BY {campo_sql}
            ORDER BY valor_empenhado DESC NULLS LAST
            LIMIT 20
        """
        rows = await pool.fetch(query, *params)
        if not rows:
            return _resposta_vazia(aviso_vazio, fonte, filtros_aplicados)
        return json.dumps({
            "modo": "ranking",
            "campo": campo_rotulo,
            "ranking": [
                {
                    "nome": r["nome"] or "N/A",
                    "quantidade": r["qtde"],
                    "empenhado": _fmt(r["valor_empenhado"]),
                    "pago": _fmt(r["valor_pago"]),
                }
                for r in rows
            ],
            "filtros": filtros_aplicados,
            "fonte": fonte,
        }, ensure_ascii=False)

    query = f"""
        SELECT autor, tipo_emenda, numero, localidade_gasto, funcao, subfuncao,
               valor_empenhado, valor_liquidado, valor_pago, ano
        FROM emendas {where_sql}
        ORDER BY valor_empenhado DESC NULLS LAST LIMIT 20
    """
    rows = await pool.fetch(query, *params)
    if not rows:
        return _resposta_vazia(aviso_vazio, fonte, filtros_aplicados)

    emendas = [{
        "autor": r["autor"],
        "tipo": r["tipo_emenda"],
        "localidade": r["localidade_gasto"],
        "funcao": r["funcao"],
        "empenhado": _fmt(r["valor_empenhado"]),
        "liquidado": _fmt(r["valor_liquidado"]),
        "pago": _fmt(r["valor_pago"]),
        "ano": r["ano"],
    } for r in rows]

    totais_query = f"SELECT SUM(valor_empenhado) AS total FROM emendas {where_sql}"
    total_row = await pool.fetchrow(totais_query, *params)

    return json.dumps({
        "modo": "lista",
        "emendas": emendas,
        "total_registros": len(emendas),
        "total_empenhado_geral": _fmt(total_row["total"]) if total_row else "N/A",
        "filtros": filtros_aplicados,
        "fonte": fonte,
    }, ensure_ascii=False)

class BuscarDadosFiscaisInput(BaseModel):
    """Busca dados fiscais (RREO/RGF) de estados e capitais."""

    ente: str | None = Field(None, description="Nome do estado ou capital (ex: 'São Paulo', 'Bahia', 'Recife')")
    exercicio: int | None = Field(None, description="Ano fiscal (ex: 2025)")
    demonstrativo: str | None = Field(None, description="Tipo: 'RREO' (execução orçamentária) ou 'RGF' (gestão fiscal)")

@tool(args_schema=BuscarDadosFiscaisInput)
async def buscar_dados_fiscais(
    ente: str | None = None,
    exercicio: int | None = None,
    demonstrativo: str | None = None,
) -> str:
    """Busca dados fiscais de estados e capitais (RREO e RGF do SICONFI). Use para perguntas sobre orçamento, receita, despesa, dívida de estados e municípios."""
    pool = get_pool()

    query = """
        SELECT e.nome AS ente_nome, e.tipo AS ente_tipo, e.uf,
               df.exercicio, df.periodo, df.demonstrativo, df.anexo,
               df.coluna, df.rotulo, df.valor
        FROM dados_fiscais df
        JOIN entes e ON df.ente_id = e.id
        WHERE 1=1
    """
    params: list = []

    if ente:
        params.append(f"%{ente}%")
        query += f" AND e.nome ILIKE ${len(params)}"
    if exercicio:
        params.append(exercicio)
        query += f" AND df.exercicio = ${len(params)}"
    if demonstrativo:
        params.append(demonstrativo.upper())
        query += f" AND df.demonstrativo = ${len(params)}"

    query += " ORDER BY df.exercicio DESC, df.periodo DESC, df.valor DESC NULLS LAST LIMIT 30"
    fonte = "SICONFI, Tesouro Nacional (dados abertos)"
    filtros = {"ente": ente, "exercicio": exercicio, "demonstrativo": demonstrativo}
    rows = await pool.fetch(query, *params)

    if not rows:
        return _resposta_vazia(
            "Nenhum dado fiscal encontrado. Verifique se o nome do ente está correto.",
            fonte,
            filtros,
        )

    dados_fiscais = [{
        "ente": r["ente_nome"],
        "tipo": r["ente_tipo"],
        "uf": r["uf"],
        "exercicio": r["exercicio"],
        "periodo": r["periodo"],
        "demonstrativo": r["demonstrativo"],
        "anexo": r["anexo"],
        "indicador": r["rotulo"],
        "coluna": r["coluna"],
        "valor": _fmt(r["valor"]),
    } for r in rows]

    return json.dumps({
        "modo": "lista",
        "dados_fiscais": dados_fiscais,
        "total_registros": len(dados_fiscais),
        "filtros": _filtros_limpos(filtros),
        "fonte": fonte,
    }, ensure_ascii=False)

class BuscarDespesasFederaisInput(BaseModel):
    """Busca execução orçamentária federal por órgão."""

    orgao: str | None = Field(None, description="Nome do órgão (ex: 'Presidência', 'Ministério da Saúde')")
    ano: int | None = Field(None, description="Ano (ex: 2025)")

@tool(args_schema=BuscarDespesasFederaisInput)
async def buscar_despesas_federais(
    orgao: str | None = None,
    ano: int | None = None,
) -> str:
    """Busca execução orçamentária federal (empenhos, liquidações, pagamentos) por órgão. Use para perguntas sobre orçamento federal, gastos de ministérios, execução orçamentária."""
    pool = get_pool()

    query = """
        SELECT orgao_superior_nome, orgao_vinculado_nome,
               SUM(valor_empenhado) AS empenhado,
               SUM(valor_liquidado) AS liquidado,
               SUM(valor_pago) AS pago,
               ano
        FROM despesas_orcamentarias WHERE 1=1
    """
    params: list = []

    if orgao:
        params.append(f"%{orgao}%")
        query += f" AND (orgao_superior_nome ILIKE ${len(params)} OR orgao_vinculado_nome ILIKE ${len(params)})"
    if ano:
        params.append(ano)
        query += f" AND ano = ${len(params)}"

    query += " GROUP BY orgao_superior_nome, orgao_vinculado_nome, ano ORDER BY empenhado DESC NULLS LAST LIMIT 20"
    fonte = "Portal da Transparência, Execução Orçamentária Federal (dados abertos)"
    filtros = {"orgao": orgao, "ano": ano}
    rows = await pool.fetch(query, *params)

    if not rows:
        return _resposta_vazia(
            "Nenhuma despesa orçamentária encontrada com os filtros informados.",
            fonte,
            filtros,
        )

    despesas = [{
        "orgao_superior": r["orgao_superior_nome"],
        "orgao_vinculado": r["orgao_vinculado_nome"],
        "empenhado": _fmt(r["empenhado"]),
        "liquidado": _fmt(r["liquidado"]),
        "pago": _fmt(r["pago"]),
        "ano": r["ano"],
    } for r in rows]

    return json.dumps({
        "modo": "lista",
        "despesas": despesas,
        "total_registros": len(despesas),
        "filtros": _filtros_limpos(filtros),
        "fonte": fonte,
    }, ensure_ascii=False)

def _link_votacao(r) -> str | None:
    """Monta link para a fonte oficial da votação."""
    if r.get("url_inteiro_teor"):
        return r["url_inteiro_teor"]
    prop_ext = r.get("proposicao_id_externo") or ""
    if prop_ext.startswith("camara-"):
        id_proposicao = prop_ext.removeprefix("camara-")
        return f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={id_proposicao}"
    if prop_ext.startswith("senado-"):
        codigo_materia = prop_ext.removeprefix("senado-")
        return f"https://www25.senado.leg.br/web/atividade/materias/-/materia/{codigo_materia}"
    return None

def _proposicao_com_link(r) -> str:
    """Formata nome da proposição como hyperlink Markdown se houver link."""
    nome = f"{r['sigla_tipo']} {r['numero']}/{r['ano']}" if r.get("sigla_tipo") else "N/A"
    link = _link_votacao(r)
    if link:
        return f"[{nome}]({link})"
    return nome

def _tipo_votacao(descricao: str | None) -> str:
    """Identifica se a votação é da proposição principal ou de emenda/destaque."""
    if not descricao:
        return "proposição"
    desc = descricao.lower()
    if "emenda" in desc or "destaque" in desc or "destacad" in desc or "subemenda" in desc:
        return "emenda/destaque"
    return "proposição"

class BuscarVotacoesInput(BaseModel):
    """Busca votações nominais da Câmara e do Senado."""

    tipo_proposicao: str | None = Field(None, description="Tipo: 'PEC', 'PL', 'PLP', 'MPV' (medida provisória), 'REQ'")
    numero_proposicao: int | None = Field(None, description="Número da proposição (ex: 3802 para PL 3802/2024)")
    parlamentar: str | None = Field(None, description="Nome do parlamentar para ver como votou")
    partido: str | None = Field(None, description="Sigla do partido para filtrar votos")
    casa: str | None = Field(None, description="'camara' ou 'senado'. Se omitido, busca ambas")
    aprovada: bool | None = Field(None, description="True para aprovadas, False para rejeitadas")
    ano: int | None = Field(None, description="Ano em que a votação ocorreu (ex: 2024, 2025)")
    voto: str | None = Field(None, description="Filtrar parlamentares pelo voto: 'Sim', 'Não', 'Abstenção', 'Obstrução'. Use junto com tipo_proposicao+numero_proposicao+ano para listar quem votou daquele jeito.")

@tool(args_schema=BuscarVotacoesInput)
async def buscar_votacoes(
    tipo_proposicao: str | None = None,
    numero_proposicao: int | None = None,
    parlamentar: str | None = None,
    partido: str | None = None,
    casa: str | None = None,
    aprovada: bool | None = None,
    ano: int | None = None,
    voto: str | None = None,
) -> str:
    """Busca votações nominais do Congresso (Câmara e Senado).

    USE para 4 cenários:
    1. LISTAR pautas/votações de um período: passe ano e/ou casa.
    2. VER COMO UM PARLAMENTAR VOTOU: passe parlamentar (nome).
    3. LISTAR QUEM VOTOU DE UM JEITO ESPECÍFICO em uma proposição: passe tipo_proposicao + numero_proposicao + ano + voto.
       Exemplos: 'quem votou contra o PL 3802/2024', 'deputados que votaram a favor da PEC 45/2024',
       'quem se absteve no PLP 68/2024'. NÃO responda que não consegue, esta tool retorna a lista completa
       de parlamentares (nome, partido, UF) para o voto especificado.
    4. BUSCAR uma proposição específica: passe tipo_proposicao + numero_proposicao + ano (sem voto).

    Valores válidos para 'voto': 'Sim', 'Não', 'Abstenção', 'Obstrução'.
    """
    pool = get_pool()
    fonte = "Dados Abertos, Câmara dos Deputados / Senado Federal"
    filtros_base = {
        "tipo_proposicao": tipo_proposicao,
        "numero_proposicao": numero_proposicao,
        "parlamentar": parlamentar,
        "partido": partido,
        "casa": casa,
        "aprovada": aprovada,
        "ano": ano,
        "voto": voto,
    }

    if voto and tipo_proposicao and numero_proposicao:
        query = """
            SELECT vt.parlamentar_nome, vt.partido, vt.uf, vt.voto,
                   v.descricao, v.sigla_tipo, v.numero, v.ano, v.casa,
                   v.aprovada, v.data_hora, v.id_externo,
                   p.url_inteiro_teor, p.id_externo AS proposicao_id_externo
            FROM votos vt
            JOIN votacoes v ON vt.votacao_id = v.id
            LEFT JOIN proposicoes p ON v.proposicao_id = p.id
            WHERE v.sigla_tipo = $1 AND v.numero = $2
              AND vt.voto ILIKE $3
        """
        params: list = [tipo_proposicao.upper(), numero_proposicao, voto]
        if ano:
            params.append(ano)
            query += f" AND EXTRACT(YEAR FROM v.data_hora) = ${len(params)}"
        if casa:
            params.append(casa.lower())
            query += f" AND v.casa = ${len(params)}"
        if partido:
            params.append(partido.upper())
            query += f" AND vt.partido = ${len(params)}"
        query += " ORDER BY v.data_hora DESC, vt.partido, vt.parlamentar_nome LIMIT 600"
        rows = await pool.fetch(query, *params)

        if not rows:
            return _resposta_vazia(
                f"Nenhum parlamentar votou '{voto}' em {tipo_proposicao} {numero_proposicao}"
                f"{f'/{ano}' if ano else ''}.",
                fonte,
                filtros_base,
            )

        votacoes_dict: dict = {}
        for r in rows:
            key = r["id_externo"]
            if key not in votacoes_dict:
                votacoes_dict[key] = {
                    "proposicao": _proposicao_com_link(r),
                    "tipo_votacao": _tipo_votacao(r["descricao"]),
                    "descricao": (r["descricao"] or "")[:200],
                    "casa": r["casa"],
                    "resultado": "Aprovada" if r["aprovada"] else "Rejeitada",
                    "data": str(r["data_hora"].date()) if r["data_hora"] else "N/A",
                    "parlamentares": [],
                }
            votacoes_dict[key]["parlamentares"].append({
                "nome": r["parlamentar_nome"],
                "partido": r["partido"],
                "uf": r["uf"],
            })

        return json.dumps({
            "modo": "parlamentares_por_voto",
            "resumo": f"{tipo_proposicao.upper()} {numero_proposicao}{f'/{ano}' if ano else ''}: voto '{voto}'",
            "votacoes": list(votacoes_dict.values()),
            "total_parlamentares": len(rows),
            "filtros": _filtros_limpos(filtros_base),
            "fonte": fonte,
        }, ensure_ascii=False)

    if parlamentar:

        query = """
            SELECT v.descricao, v.sigla_tipo, v.numero, v.ano, v.casa,
                   v.aprovada, v.data_hora, v.id_externo,
                   vt.voto, vt.partido, vt.uf,
                   p.url_inteiro_teor, p.id_externo AS proposicao_id_externo
            FROM votos vt
            JOIN votacoes v ON vt.votacao_id = v.id
            LEFT JOIN proposicoes p ON v.proposicao_id = p.id
            WHERE vt.parlamentar_nome ILIKE $1
        """
        params: list = [f"%{parlamentar}%"]

        if tipo_proposicao:
            params.append(tipo_proposicao.upper())
            query += f" AND v.sigla_tipo = ${len(params)}"
        if numero_proposicao:
            params.append(numero_proposicao)
            query += f" AND v.numero = ${len(params)}"
        if casa:
            params.append(casa.lower())
            query += f" AND v.casa = ${len(params)}"
        if ano:
            params.append(ano)
            query += f" AND EXTRACT(YEAR FROM v.data_hora) = ${len(params)}"

        query += " ORDER BY v.data_hora DESC LIMIT 20"
        rows = await pool.fetch(query, *params)

        if not rows:
            return _resposta_vazia(
                f"Nenhum voto encontrado para '{parlamentar}'.",
                fonte,
                filtros_base,
            )

        votos = [{
            "proposicao": _proposicao_com_link(r),
            "tipo_votacao": _tipo_votacao(r["descricao"]),
            "descricao": (r["descricao"] or "")[:150],
            "casa": r["casa"],
            "voto": r["voto"],
            "resultado": "Aprovada" if r["aprovada"] else "Rejeitada",
            "data": str(r["data_hora"].date()) if r["data_hora"] else "N/A",
        } for r in rows]

        return json.dumps({
            "modo": "votos_parlamentar",
            "parlamentar": parlamentar,
            "votos": votos,
            "total_registros": len(votos),
            "filtros": _filtros_limpos(filtros_base),
            "fonte": fonte,
        }, ensure_ascii=False)

    else:

        filtros = ["v.sigla_tipo != 'REQ'"]
        procedurais = [
            "%redação final%", "%redacao final%",
            "%mantido o texto%",
            "%quebra de interstício%", "%quebra de intersticio%",
            "%adiamento%", "%retirada de pauta%",
            "%encerramento da discussão%",
        ]
        for padrao in procedurais:
            filtros.append(f"COALESCE(v.descricao, '') NOT ILIKE '{padrao}'")
        filtros_sql = " AND ".join(filtros)

        query = f"""
            WITH votacoes_filtradas AS (
                SELECT v.id, v.descricao, v.sigla_tipo, v.numero, v.ano, v.casa,
                       v.aprovada, v.data_hora, v.votos_sim, v.votos_nao, v.votos_abstencao,
                       v.id_externo, p.url_inteiro_teor,
                       p.id_externo AS proposicao_id_externo,
                       ROW_NUMBER() OVER (
                           PARTITION BY v.casa, v.descricao
                           ORDER BY v.data_hora DESC
                       ) AS rn
                FROM votacoes v
                LEFT JOIN proposicoes p ON v.proposicao_id = p.id
                WHERE {filtros_sql}
        """
        params = []

        if tipo_proposicao:
            params.append(tipo_proposicao.upper())
            query += f" AND v.sigla_tipo = ${len(params)}"
        if numero_proposicao:
            params.append(numero_proposicao)
            query += f" AND v.numero = ${len(params)}"
        if casa:
            params.append(casa.lower())
            query += f" AND v.casa = ${len(params)}"
        if aprovada is not None:
            params.append(aprovada)
            query += f" AND v.aprovada = ${len(params)}"
        if ano:
            params.append(ano)
            query += f" AND EXTRACT(YEAR FROM v.data_hora) = ${len(params)}"

        query += """
            )
            SELECT * FROM votacoes_filtradas
            WHERE rn = 1
            ORDER BY data_hora DESC
            LIMIT 15
        """
        rows = await pool.fetch(query, *params)

        if not rows:
            return _resposta_vazia("Nenhuma votação encontrada com os filtros informados.", fonte, filtros_base)

        votacoes = []
        for r in rows:
            item = {
                "proposicao": _proposicao_com_link(r),
                "tipo_votacao": _tipo_votacao(r["descricao"]),
                "descricao": (r["descricao"] or "")[:200],
                "casa": r["casa"],
                "resultado": "Aprovada" if r["aprovada"] else "Rejeitada",
                "sim": r["votos_sim"],
                "nao": r["votos_nao"],
                "abstencao": r["votos_abstencao"],
                "data": str(r["data_hora"].date()) if r["data_hora"] else "N/A",
            }

            if partido:
                votos_partido = await pool.fetch(
                    """SELECT parlamentar_nome, voto FROM votos
                    WHERE votacao_id = $1 AND partido = $2""",
                    r["id"], partido.upper(),
                )
                if votos_partido:
                    item["votos_partido"] = {v["parlamentar_nome"]: v["voto"] for v in votos_partido}

            votacoes.append(item)

        return json.dumps({
            "modo": "lista",
            "votacoes": votacoes,
            "total_registros": len(votacoes),
            "filtros": _filtros_limpos(filtros_base),
            "fonte": fonte,
        }, ensure_ascii=False)

ALL_TOOLS = [
    buscar_despesas, ranking_despesas, listar_parlamentares,
    listar_executivos,
    buscar_suspeitas, consultar_recibo, buscar_empresa, buscar_similar,
    explicar_termo,
    buscar_cpgf, buscar_contratos, buscar_viagens,
    buscar_emendas, buscar_dados_fiscais, buscar_despesas_federais,
    buscar_votacoes,
]
