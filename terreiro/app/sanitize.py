"""
Camada de validação e normalização de dados (Silver Layer).

Todas as funções de sanitização são aplicadas ANTES do INSERT no banco.
Garantem precisão e veracidade dos dados usados pela LLM e tools.
"""

import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

UFS_VALIDAS = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
}

def limpar_documento(val: str | None) -> str | None:
    """Remove formatação de CNPJ/CPF, retorna só dígitos ou None."""
    if not val:
        return None
    digits = re.sub(r"[.\-/\s]", "", str(val)).strip()
    if not digits or not digits.isdigit():
        return None
    return digits if len(digits) in (11, 14) else None

def validar_cpf(cpf: str) -> bool:
    """Valida dígitos verificadores de CPF (11 dígitos)."""
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in (9, 10):
        soma = sum(int(cpf[j]) * ((i + 1) - j) for j in range(i))
        digito = (soma * 10 % 11) % 10
        if int(cpf[i]) != digito:
            return False
    return True

def validar_cnpj(cnpj: str) -> bool:
    """Valida dígitos verificadores de CNPJ (14 dígitos)."""
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    d1 = 11 - (soma % 11)
    d1 = 0 if d1 >= 10 else d1
    if int(cnpj[12]) != d1:
        return False
    soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    d2 = 11 - (soma % 11)
    d2 = 0 if d2 >= 10 else d2
    return int(cnpj[13]) == d2

def validar_documento(val: str | None) -> tuple[str | None, bool]:
    """Limpa e valida CPF/CNPJ. Retorna (documento_limpo, é_válido)."""
    doc = limpar_documento(val)
    if not doc:
        return None, False
    if len(doc) == 11:
        return doc, validar_cpf(doc)
    return doc, validar_cnpj(doc)

def normalizar_uf(val: str | None) -> str | None:
    """Normaliza UF para 2 letras maiúsculas. Retorna None se inválida."""
    if not val:
        return None
    uf = val.strip().upper()[:2]
    return uf if uf in UFS_VALIDAS else None

def normalizar_partido(val: str | None) -> str | None:
    """Normaliza sigla de partido para maiúsculas."""
    if not val:
        return None
    return val.strip().upper() or None

def normalizar_valor(val, default=None, limite: Decimal | None = Decimal("10000000.00")) -> Decimal | None:
    """Converte para Decimal com 2 casas. Aceita formato BR ('1.234,56') e numérico.
    limite=None desabilita o limite superior (para orçamentos federais/estaduais)."""
    if val is None or val == "":
        return default
    s = str(val).strip()

    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        d = Decimal(s).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if limite and abs(d) > limite:
            return default
        return d
    except (InvalidOperation, ValueError, TypeError):
        return default

def normalizar_valor_positivo(val, default=None) -> Decimal | None:
    """Converte para Decimal >= 0 com 2 casas."""
    d = normalizar_valor(val, default)
    if d is not None and d < 0:
        return default
    return d

def normalizar_data(val: str | None) -> date | None:
    """Parseia data em vários formatos, rejeita fora de [2000, ano_atual+1]."""
    if not val:
        return None
    val = val.strip()
    d = None

    try:
        d = date.fromisoformat(val[:10])
    except (ValueError, TypeError):
        pass

    if d is None and "/" in val:
        parts = val.split("/")
        if len(parts) == 3:
            try:
                d = date(int(parts[2]), int(parts[1]), int(parts[0]))
            except (ValueError, IndexError):
                pass

    if d is None and len(val) == 8 and val.isdigit():
        try:
            d = date(int(val[:4]), int(val[4:6]), int(val[6:8]))
        except ValueError:
            pass

    if d is None:
        return None

    ano_max = date.today().year + 1
    if d.year < 2000 or d.year > ano_max:
        return None
    return d

def normalizar_ano(val, default: int | None = None) -> int | None:
    """Valida ano entre 2000 e ano_atual+1."""
    if val is None or val == "":
        return default
    try:
        a = int(val)
    except (ValueError, TypeError):
        return default
    ano_max = date.today().year + 1
    return a if 2000 <= a <= ano_max else default

def normalizar_mes(val, default: int = 0) -> int:
    """Valida mês entre 1-12. Retorna default se inválido."""
    if val is None or val == "":
        return default
    try:
        m = int(val)
    except (ValueError, TypeError):
        return default
    return m if 1 <= m <= 12 else default

def normalizar_texto(val: str | None, max_len: int | None = None) -> str | None:
    """Limpa texto: strip, coalesce vazio para None, trunca se necessário."""
    if not val:
        return None
    t = val.strip()
    if not t:
        return None
    if max_len and len(t) > max_len:
        t = t[:max_len]
    return t

def normalizar_nome(val: str | None) -> str | None:
    """Normaliza nome: title case, strip."""
    t = normalizar_texto(val, max_len=200)
    if not t:
        return None

    if t == t.upper():
        return t.title()
    return t

def normalizar_email(val: str | None) -> str | None:
    """Normaliza email: lowercase, strip, valida formato básico."""
    t = normalizar_texto(val, max_len=200)
    if not t:
        return None
    t = t.lower()
    if "@" not in t or "." not in t:
        return None
    return t

def to_int(val, default: int | None = None) -> int | None:
    if val is None or val == "":
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default
