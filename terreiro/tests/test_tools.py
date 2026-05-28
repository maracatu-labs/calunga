"""Testes de golden-path das tools do Calunga.

Pool asyncpg e mockado via fixture install_pool; cada teste controla o
retorno de fetch/fetchrow para cobrir os caminhos principais:
- sucesso (modo lista, ranking, item, resumo)
- vazio (modo 'vazio' com aviso)
- erro de input (modo 'erro')
"""

from __future__ import annotations

import json

import pytest

from tests.conftest import record


async def _invoke(tool, **kwargs) -> dict:
    """Helper: chama a tool (LangChain @tool) e desserializa o retorno."""
    result = await tool.ainvoke(kwargs)
    return json.loads(result)

class TestFiltroOrgao:
    """Helper interno mas critico (task #2: bug SQL corrigido).

    A funcao virou async apos a task #16 (resolucao de sinonimos via
    tabela orgaos_federais). O cache de aliases e mockado nos testes
    para nao tocar o banco.
    """

    @pytest.fixture(autouse=True)
    def fake_aliases(self, monkeypatch):
        from app.agent import tools as tools_module

        async def fake_cache():
            return {
                "planalto": "20000",
                "presidência da república": "20000",
                "mec": "26000",
                "ministério da educação": "26000",
            }
        monkeypatch.setattr(tools_module, "_carregar_aliases_orgaos", fake_cache)

    @pytest.mark.asyncio
    async def test_nome_textual_desconhecido_vira_ilike(self):
        from app.agent.tools import _filtro_orgao
        params = []
        clause = await _filtro_orgao(params, "Ministério Inexistente")
        assert clause == "orgao_nome ILIKE $1"
        assert params == ["%Ministério Inexistente%"]

    @pytest.mark.asyncio
    async def test_codigo_numerico_vira_match_exato(self):
        from app.agent.tools import _filtro_orgao
        params = [42]
        clause = await _filtro_orgao(params, "20000")
        assert clause == "orgao_codigo = $2"
        assert params == [42, "20000"]

    @pytest.mark.asyncio
    async def test_nome_com_digitos_internos_vai_para_ilike(self):
        from app.agent.tools import _filtro_orgao
        params = []
        clause = await _filtro_orgao(params, "GSI 4")
        assert clause == "orgao_nome ILIKE $1"

    @pytest.mark.asyncio
    async def test_alias_popular_resolve_para_codigo(self):
        """'Planalto' -> '20000' via tabela orgaos_federais."""
        from app.agent.tools import _filtro_orgao
        params = []
        clause = await _filtro_orgao(params, "Planalto")
        assert clause == "orgao_codigo = $1"
        assert params == ["20000"]

    @pytest.mark.asyncio
    async def test_nome_oficial_tambem_resolve_para_codigo(self):
        from app.agent.tools import _filtro_orgao
        params = []
        clause = await _filtro_orgao(params, "Ministério da Educação")
        assert clause == "orgao_codigo = $1"
        assert params == ["26000"]

    @pytest.mark.asyncio
    async def test_alias_e_case_insensitive(self):
        from app.agent.tools import _filtro_orgao
        params = []
        clause = await _filtro_orgao(params, "mec")
        assert clause == "orgao_codigo = $1"
        assert params == ["26000"]

class TestBuscarCPGF:
    @pytest.mark.asyncio
    async def test_lista_vazia_retorna_modo_vazio(self, install_pool):
        install_pool.fetch.return_value = []

        from app.agent.tools import buscar_cpgf
        data = await _invoke(buscar_cpgf, orgao="Presidência", ano=2023)

        assert data["modo"] == "vazio"
        assert "aviso" in data
        assert data["filtros"]["ano"] == 2023
        assert data["fonte"].startswith("CPGF")

    @pytest.mark.asyncio
    async def test_listagem_simples(self, install_pool):
        install_pool.fetch.return_value = [
            record(
                orgao_nome="Presidência da República",
                portador_nome="João Silva",
                favorecido_nome="Restaurante X",
                transacao="PAGAMENTO",
                valor=500.0,
                data_transacao=None,
                mes_extrato=3,
                ano_extrato=2025,
            ),
        ]
        install_pool.fetchrow.return_value = record(total=1, valor_total=500.0)

        from app.agent.tools import buscar_cpgf
        data = await _invoke(buscar_cpgf, orgao="Presidência")

        assert data["modo"] == "lista"
        assert len(data["gastos"]) == 1
        assert data["gastos"][0]["portador"] == "João Silva"
        assert data["total_registros"] == 1

    @pytest.mark.asyncio
    async def test_ranking_por_orgao(self, install_pool):
        install_pool.fetch.return_value = [
            record(nome="Casa Civil", qtde=50, valor_total=120000.0),
            record(nome="Presidência", qtde=30, valor_total=80000.0),
        ]

        from app.agent.tools import buscar_cpgf
        data = await _invoke(buscar_cpgf, agrupar_por="orgao", ano=2025)

        assert data["modo"] == "ranking"
        assert data["campo"] == "órgão"
        assert data["ranking"][0]["nome"] == "Casa Civil"
        assert data["ranking"][0]["quantidade"] == 50

    @pytest.mark.asyncio
    async def test_agrupar_invalido_retorna_erro(self, install_pool):
        from app.agent.tools import buscar_cpgf
        data = await _invoke(buscar_cpgf, agrupar_por="xpto")

        assert data["modo"] == "erro"
        assert "agrupar_por" in data["erro"]

class TestBuscarEmendas:
    @pytest.mark.asyncio
    async def test_ranking_por_autor_inclui_empenhado_e_pago(self, install_pool):
        install_pool.fetch.return_value = [
            record(nome="Fulano", qtde=12, valor_empenhado=1_000_000.0, valor_pago=800_000.0),
        ]

        from app.agent.tools import buscar_emendas
        data = await _invoke(buscar_emendas, agrupar_por="autor", tipo="pix")

        assert data["modo"] == "ranking"
        assert data["ranking"][0]["empenhado"].startswith("R$")
        assert data["ranking"][0]["pago"].startswith("R$")
        assert data["filtros"]["tipo"] == "pix"

class TestListarExecutivos:
    @pytest.mark.asyncio
    async def test_cargo_invalido_retorna_erro(self, install_pool):
        from app.agent.tools import listar_executivos
        data = await _invoke(listar_executivos, cargo="ministro")

        assert data["modo"] == "erro"
        assert "cargo" in data["erro"]

    @pytest.mark.asyncio
    async def test_sem_filtros_lista_tres_cargos(self, install_pool):
        install_pool.fetch.return_value = [
            record(id=1, nome="Gov SP", tipo="governador", partido="PSDB", uf="SP",
                   situacao="Exercício", ente_nome="São Paulo", ente_tipo="estado"),
            record(id=2, nome="Prefeito Recife", tipo="prefeito", partido="PSB", uf="PE",
                   situacao="Exercício", ente_nome="Recife", ente_tipo="capital"),
        ]

        from app.agent.tools import listar_executivos
        data = await _invoke(listar_executivos)

        assert data["modo"] == "lista"
        assert data["total_registros"] == 2
        assert {e["cargo"] for e in data["executivos"]} == {"governador", "prefeito"}

class TestRankingDespesas:
    @pytest.mark.asyncio
    async def test_ranking_com_dados(self, install_pool, monkeypatch):
        from app.agent import tools as tools_module

        async def fake_ranking(pool, **kwargs):
            return [
                record(nome="Deputado A", tipo="deputado", partido="PT", uf="SP",
                       total_registros=120, valor_total=500000.0),
            ]
        monkeypatch.setattr(
            tools_module.despesas_q, "ranking_deputados_por_gasto", fake_ranking
        )

        data = await _invoke(tools_module.ranking_despesas, tipo="deputado", ano=2024)

        assert data["modo"] == "ranking"
        assert data["campo"] == "parlamentar"
        assert data["ranking"][0]["posicao"] == 1
        assert "R$" in data["ranking"][0]["valor_total"]

    @pytest.mark.asyncio
    async def test_ranking_vazio(self, install_pool, monkeypatch):
        from app.agent import tools as tools_module

        async def fake_ranking(pool, **kwargs):
            return []
        monkeypatch.setattr(
            tools_module.despesas_q, "ranking_deputados_por_gasto", fake_ranking
        )

        data = await _invoke(tools_module.ranking_despesas, ano=2099)

        assert data["modo"] == "vazio"
        assert data["filtros"]["ano"] == 2099

class TestConsultarRecibo:
    @pytest.mark.asyncio
    async def test_sem_analise_retorna_vazio(self, install_pool):
        install_pool.fetchrow.return_value = None

        from app.agent.tools import consultar_recibo
        data = await _invoke(consultar_recibo, despesa_id=999)

        assert data["modo"] == "vazio"
        assert data["filtros"]["despesa_id"] == 999

    @pytest.mark.asyncio
    async def test_retorna_analise_estruturada(self, install_pool):
        detalhes = {
            "itens": [{"descricao": "Whisky", "quantidade": 1, "valor": 90.0}],
            "tem_alcool": True,
            "itens_discriminados": True,
            "valor_total": 90.0,
            "irregularidades": ["consumo de bebida alcoolica"],
        }
        install_pool.fetchrow.return_value = record(
            detalhes=json.dumps(detalhes),
            probabilidade=0.8,
            fornecedor="Bar do Zé",
            cnpj_cpf="12345678000100",
            valor_liquido=90.0,
            data_emissao=None,
            categoria="Alimentação",
            url_documento="https://exemplo.gov.br/recibo.pdf",
            parlamentar_nome="Deputado X",
            partido="PL",
            uf="SP",
            parlamentar_id_externo="camara-123",
            parlamentar_tipo="deputado",
        )

        from app.agent.tools import consultar_recibo
        data = await _invoke(consultar_recibo, despesa_id=42)

        assert data["modo"] == "item"
        assert data["despesa_id"] == 42
        assert data["analise"]["tem_alcool"] is True
        assert data["analise"]["irregularidades"] == ["consumo de bebida alcoolica"]

        assert "[Deputado X](" in data["parlamentar"]
