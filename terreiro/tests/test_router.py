"""Testes do model router do Calunga."""

import pytest

from app.agent.router import fallback_model, route_model


class TestRouteModel:
    @pytest.mark.parametrize("pergunta", [
        "Quanto o deputado Lula gastou em 2024?",
        "Lista os senadores de SP",
        "Ranking dos 10 que mais gastaram",
        "Top 5 fornecedores do governo",
        "Quais contratos o MEC tem?",
        "Quem sao os deputados do PT?",
        "Qual o CNPJ da empresa X?",
        "Busque emendas Pix em Pernambuco",
    ])
    def test_queries_simples_vao_para_flash(self, pergunta):
        assert route_model(pergunta) == "gemini-2.5-flash"

    @pytest.mark.parametrize("pergunta", [
        "Compare os gastos de Lula e Bolsonaro em 2024",
        "Analise o padrao de gastos do deputado Fulano",
        "Analisar evolucao do cartao corporativo",
        "Por que o gasto subiu em 2024?",
        "Investigue suspeitas no gabinete X",
        "Cruzar dados de emendas com contratos",
        "Qual a evolucao da receita do estado em 2025?",
        "Descreva o padrao de comportamento do PSD",
        "Correlacione CPGF e emendas Pix",
        "Me traga o detalhe completo do deputado X",
    ])
    def test_queries_complexas_vao_para_pro(self, pergunta):
        assert route_model(pergunta) == "gemini-2.5-pro"

    def test_default_model_respeitado_em_queries_simples(self):
        assert route_model("lista de deputados", default_model="custom-model") == "custom-model"

class TestFallbackModel:
    def test_pro_cai_para_flash(self):
        assert fallback_model("gemini-2.5-pro") == "gemini-2.5-flash"

    def test_flash_nao_tem_fallback(self):
        assert fallback_model("gemini-2.5-flash") is None

    def test_modelo_desconhecido_nao_tem_fallback(self):
        assert fallback_model("outro-modelo") is None
