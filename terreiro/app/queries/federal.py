"""Queries para dados federais: CPGF, despesas orçamentárias, contratos, licitações, viagens, emendas."""

import asyncpg

from app.sanitize import (
    limpar_documento,
    normalizar_ano,
    normalizar_data,
    normalizar_mes,
    normalizar_texto,
    normalizar_valor,
    to_int,
)


async def upsert_cpgf(pool: asyncpg.Pool, **data) -> asyncpg.Record:
    return await pool.fetchrow(
        """
        INSERT INTO cpgf (id_externo, orgao_codigo, orgao_nome, unidade_gestora_codigo,
                          unidade_gestora_nome, portador_nome, portador_cpf, tipo_cartao,
                          transacao, cnpj_cpf_favorecido, favorecido_nome, valor,
                          data_transacao, mes_extrato, ano_extrato)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
        ON CONFLICT (id_externo) DO UPDATE SET
            valor = EXCLUDED.valor,
            favorecido_nome = EXCLUDED.favorecido_nome
        RETURNING *
        """,
        normalizar_texto(data.get("id_externo"), max_len=200),
        normalizar_texto(data.get("orgao_codigo"), max_len=10),
        normalizar_texto(data.get("orgao_nome"), max_len=200),
        normalizar_texto(data.get("unidade_gestora_codigo"), max_len=10),
        normalizar_texto(data.get("unidade_gestora_nome"), max_len=200),
        normalizar_texto(data.get("portador_nome"), max_len=200),
        limpar_documento(data.get("portador_cpf")),
        normalizar_texto(data.get("tipo_cartao"), max_len=50),
        normalizar_texto(data.get("transacao"), max_len=200),
        limpar_documento(data.get("cnpj_cpf_favorecido")),
        normalizar_texto(data.get("favorecido_nome"), max_len=200),
        normalizar_valor(data.get("valor")),
        normalizar_data(data.get("data_transacao")) if isinstance(data.get("data_transacao"), str) else data.get("data_transacao"),
        normalizar_mes(data.get("mes_extrato")),
        normalizar_ano(data.get("ano_extrato")),
    )

async def upsert_despesa_orcamentaria(pool: asyncpg.Pool, **data) -> asyncpg.Record:
    return await pool.fetchrow(
        """
        INSERT INTO despesas_orcamentarias (id_externo, ano, orgao_superior_codigo, orgao_superior_nome,
                          orgao_vinculado_codigo, orgao_vinculado_nome, unidade_gestora_codigo,
                          unidade_gestora_nome, funcao, subfuncao, programa, acao,
                          categoria_economica, grupo_despesa, elemento_despesa, modalidade_licitacao,
                          favorecido_nome, favorecido_cnpj_cpf,
                          valor_empenhado, valor_liquidado, valor_pago, valor_resto_pago)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22)
        ON CONFLICT (id_externo) DO UPDATE SET
            valor_empenhado = EXCLUDED.valor_empenhado,
            valor_liquidado = EXCLUDED.valor_liquidado,
            valor_pago = EXCLUDED.valor_pago,
            valor_resto_pago = EXCLUDED.valor_resto_pago
        RETURNING *
        """,
        normalizar_texto(data.get("id_externo"), max_len=200),
        normalizar_ano(data.get("ano")),
        normalizar_texto(data.get("orgao_superior_codigo"), max_len=10),
        normalizar_texto(data.get("orgao_superior_nome"), max_len=200),
        normalizar_texto(data.get("orgao_vinculado_codigo"), max_len=10),
        normalizar_texto(data.get("orgao_vinculado_nome"), max_len=200),
        normalizar_texto(data.get("unidade_gestora_codigo"), max_len=10),
        normalizar_texto(data.get("unidade_gestora_nome"), max_len=200),
        normalizar_texto(data.get("funcao"), max_len=100),
        normalizar_texto(data.get("subfuncao"), max_len=100),
        normalizar_texto(data.get("programa"), max_len=200),
        normalizar_texto(data.get("acao"), max_len=200),
        normalizar_texto(data.get("categoria_economica"), max_len=100),
        normalizar_texto(data.get("grupo_despesa"), max_len=100),
        normalizar_texto(data.get("elemento_despesa"), max_len=200),
        normalizar_texto(data.get("modalidade_licitacao"), max_len=100),
        normalizar_texto(data.get("favorecido_nome"), max_len=300),
        limpar_documento(data.get("favorecido_cnpj_cpf")),
        normalizar_valor(data.get("valor_empenhado"), limite=None),
        normalizar_valor(data.get("valor_liquidado"), limite=None),
        normalizar_valor(data.get("valor_pago"), limite=None),
        normalizar_valor(data.get("valor_resto_pago"), limite=None),
    )

async def upsert_contrato(pool: asyncpg.Pool, **data) -> asyncpg.Record:
    return await pool.fetchrow(
        """
        INSERT INTO contratos (id_externo, orgao_codigo, orgao_nome, unidade_gestora_codigo,
                               unidade_gestora_nome, fornecedor_nome, fornecedor_cnpj_cpf,
                               objeto, numero, modalidade_licitacao, situacao,
                               valor_inicial, valor_final, valor_acumulado,
                               data_inicio, data_fim, data_publicacao)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)
        ON CONFLICT (id_externo) DO UPDATE SET
            situacao = EXCLUDED.situacao,
            valor_final = EXCLUDED.valor_final,
            valor_acumulado = EXCLUDED.valor_acumulado
        RETURNING *
        """,
        normalizar_texto(data.get("id_externo"), max_len=200),
        normalizar_texto(data.get("orgao_codigo"), max_len=10),
        normalizar_texto(data.get("orgao_nome"), max_len=200),
        normalizar_texto(data.get("unidade_gestora_codigo"), max_len=10),
        normalizar_texto(data.get("unidade_gestora_nome"), max_len=200),
        normalizar_texto(data.get("fornecedor_nome"), max_len=300),
        limpar_documento(data.get("fornecedor_cnpj_cpf")),
        normalizar_texto(data.get("objeto")),
        normalizar_texto(data.get("numero"), max_len=50),
        normalizar_texto(data.get("modalidade_licitacao"), max_len=100),
        normalizar_texto(data.get("situacao"), max_len=50),
        normalizar_valor(data.get("valor_inicial")),
        normalizar_valor(data.get("valor_final")),
        normalizar_valor(data.get("valor_acumulado")),
        normalizar_data(data.get("data_inicio")) if isinstance(data.get("data_inicio"), str) else data.get("data_inicio"),
        normalizar_data(data.get("data_fim")) if isinstance(data.get("data_fim"), str) else data.get("data_fim"),
        normalizar_data(data.get("data_publicacao")) if isinstance(data.get("data_publicacao"), str) else data.get("data_publicacao"),
    )

async def upsert_licitacao(pool: asyncpg.Pool, **data) -> asyncpg.Record:
    return await pool.fetchrow(
        """
        INSERT INTO licitacoes (id_externo, orgao_codigo, orgao_nome, unidade_gestora_codigo,
                                unidade_gestora_nome, modalidade, numero, objeto, situacao,
                                valor_estimado, valor_homologado,
                                data_abertura, data_resultado, data_publicacao)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
        ON CONFLICT (id_externo) DO UPDATE SET
            situacao = EXCLUDED.situacao,
            valor_homologado = EXCLUDED.valor_homologado
        RETURNING *
        """,
        normalizar_texto(data.get("id_externo"), max_len=200),
        normalizar_texto(data.get("orgao_codigo"), max_len=10),
        normalizar_texto(data.get("orgao_nome"), max_len=200),
        normalizar_texto(data.get("unidade_gestora_codigo"), max_len=10),
        normalizar_texto(data.get("unidade_gestora_nome"), max_len=200),
        normalizar_texto(data.get("modalidade"), max_len=100),
        normalizar_texto(data.get("numero"), max_len=50),
        normalizar_texto(data.get("objeto")),
        normalizar_texto(data.get("situacao"), max_len=50),
        normalizar_valor(data.get("valor_estimado")),
        normalizar_valor(data.get("valor_homologado")),
        normalizar_data(data.get("data_abertura")) if isinstance(data.get("data_abertura"), str) else data.get("data_abertura"),
        normalizar_data(data.get("data_resultado")) if isinstance(data.get("data_resultado"), str) else data.get("data_resultado"),
        normalizar_data(data.get("data_publicacao")) if isinstance(data.get("data_publicacao"), str) else data.get("data_publicacao"),
    )

async def upsert_viagem(pool: asyncpg.Pool, **data) -> asyncpg.Record:
    return await pool.fetchrow(
        """
        INSERT INTO viagens (id_externo, orgao_codigo, orgao_nome, viajante_nome, viajante_cpf,
                             cargo, destino, motivo, urgente, data_ida, data_volta,
                             valor_passagens, valor_diarias, valor_outros)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
        ON CONFLICT (id_externo) DO UPDATE SET
            valor_passagens = EXCLUDED.valor_passagens,
            valor_diarias = EXCLUDED.valor_diarias,
            valor_outros = EXCLUDED.valor_outros
        RETURNING *
        """,
        normalizar_texto(data.get("id_externo"), max_len=200),
        normalizar_texto(data.get("orgao_codigo"), max_len=10),
        normalizar_texto(data.get("orgao_nome"), max_len=200),
        normalizar_texto(data.get("viajante_nome"), max_len=200),
        limpar_documento(data.get("viajante_cpf")),
        normalizar_texto(data.get("cargo"), max_len=200),
        normalizar_texto(data.get("destino"), max_len=200),
        normalizar_texto(data.get("motivo")),
        bool(data.get("urgente", False)),
        normalizar_data(data.get("data_ida")) if isinstance(data.get("data_ida"), str) else data.get("data_ida"),
        normalizar_data(data.get("data_volta")) if isinstance(data.get("data_volta"), str) else data.get("data_volta"),
        normalizar_valor(data.get("valor_passagens")),
        normalizar_valor(data.get("valor_diarias")),
        normalizar_valor(data.get("valor_outros")),
    )

async def upsert_emenda(pool: asyncpg.Pool, **data) -> asyncpg.Record:
    return await pool.fetchrow(
        """
        INSERT INTO emendas (id_externo, ano, autor, tipo_emenda, numero,
                             localidade_gasto, funcao, subfuncao,
                             valor_empenhado, valor_liquidado, valor_pago)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
        ON CONFLICT (id_externo) DO UPDATE SET
            valor_empenhado = EXCLUDED.valor_empenhado,
            valor_liquidado = EXCLUDED.valor_liquidado,
            valor_pago = EXCLUDED.valor_pago
        RETURNING *
        """,
        normalizar_texto(data.get("id_externo"), max_len=200),
        normalizar_ano(data.get("ano")),
        normalizar_texto(data.get("autor"), max_len=200),
        normalizar_texto(data.get("tipo_emenda"), max_len=50),
        normalizar_texto(data.get("numero"), max_len=20),
        normalizar_texto(data.get("localidade_gasto"), max_len=200),
        normalizar_texto(data.get("funcao"), max_len=100),
        normalizar_texto(data.get("subfuncao"), max_len=100),
        normalizar_valor(data.get("valor_empenhado"), limite=None),
        normalizar_valor(data.get("valor_liquidado"), limite=None),
        normalizar_valor(data.get("valor_pago"), limite=None),
    )

async def upsert_dado_fiscal(pool: asyncpg.Pool, **data) -> None:
    await pool.execute(
        """
        INSERT INTO dados_fiscais (ente_id, exercicio, periodo, demonstrativo, anexo, coluna, rotulo, valor)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (ente_id, exercicio, periodo, demonstrativo, anexo, coluna, rotulo)
        DO UPDATE SET valor = EXCLUDED.valor
        """,
        data.get("ente_id"),
        normalizar_ano(data.get("exercicio")),
        to_int(data.get("periodo"), 1),
        normalizar_texto(data.get("demonstrativo"), max_len=10),
        normalizar_texto(data.get("anexo"), max_len=100),
        normalizar_texto(data.get("coluna"), max_len=200),
        normalizar_texto(data.get("rotulo"), max_len=500),
        normalizar_valor(data.get("valor"), limite=None),
    )
