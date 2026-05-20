"""Testes dos classificadores de anomalias (Gonguê)."""

from app.classifiers.cnpj_cpf_invalido import _validate_cpf, _validate_cnpj

class TestValidateCPF:
    def test_cpf_valido(self):
        assert _validate_cpf("52998224725") is True

    def test_cpf_invalido_digitos(self):
        assert _validate_cpf("52998224720") is False

    def test_cpf_todos_iguais(self):
        assert _validate_cpf("11111111111") is False

    def test_cpf_com_zeros(self):
        assert _validate_cpf("00000000000") is False

    def test_cpf_curto_com_padding(self):

        assert _validate_cpf("1234567") is False

class TestValidateCNPJ:
    def test_cnpj_valido(self):
        assert _validate_cnpj("11222333000181") is True

    def test_cnpj_invalido_digitos(self):
        assert _validate_cnpj("11222333000180") is False

    def test_cnpj_curto(self):
        assert _validate_cnpj("123") is False

    def test_cnpj_receita_federal(self):

        assert _validate_cnpj("00394460000141") is True

    def test_cnpj_invalido_completo(self):
        assert _validate_cnpj("12345678901234") is False
