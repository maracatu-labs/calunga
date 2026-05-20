"""Queries para votações, votos individuais, orientações e proposições."""

import asyncpg

from app.sanitize import (
    normalizar_ano,
    normalizar_partido,
    normalizar_texto,
    normalizar_uf,
    to_int,
)

async def upsert_proposicao(pool: asyncpg.Pool, **data) -> asyncpg.Record:
    return await pool.fetchrow(
        """
        INSERT INTO proposicoes (id_externo, casa, sigla_tipo, numero, ano, ementa,
                                 data_apresentacao, autor, tema, url_inteiro_teor)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
        ON CONFLICT (id_externo) DO UPDATE SET
            ementa = COALESCE(EXCLUDED.ementa, proposicoes.ementa),
            autor = COALESCE(EXCLUDED.autor, proposicoes.autor)
        RETURNING *
        """,
        normalizar_texto(data.get("id_externo"), max_len=50),
        data.get("casa"),
        normalizar_texto(data.get("sigla_tipo"), max_len=10),
        to_int(data.get("numero")),
        normalizar_ano(data.get("ano")),
        normalizar_texto(data.get("ementa")),
        data.get("data_apresentacao"),
        normalizar_texto(data.get("autor"), max_len=300),
        normalizar_texto(data.get("tema"), max_len=200),
        normalizar_texto(data.get("url_inteiro_teor")),
    )

async def upsert_votacao(pool: asyncpg.Pool, **data) -> asyncpg.Record:
    return await pool.fetchrow(
        """
        INSERT INTO votacoes (id_externo, casa, proposicao_id, sigla_tipo, numero, ano,
                              descricao, data_hora, orgao, aprovada,
                              votos_sim, votos_nao, votos_abstencao, votacao_secreta)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
        ON CONFLICT (id_externo) DO UPDATE SET
            descricao = EXCLUDED.descricao,
            aprovada = EXCLUDED.aprovada,
            votos_sim = EXCLUDED.votos_sim,
            votos_nao = EXCLUDED.votos_nao,
            votos_abstencao = EXCLUDED.votos_abstencao
        RETURNING *
        """,
        normalizar_texto(data.get("id_externo"), max_len=100),
        data.get("casa"),
        data.get("proposicao_id"),
        normalizar_texto(data.get("sigla_tipo"), max_len=10),
        to_int(data.get("numero")),
        normalizar_ano(data.get("ano")),
        normalizar_texto(data.get("descricao")),
        data.get("data_hora"),
        normalizar_texto(data.get("orgao"), max_len=50),
        data.get("aprovada"),
        to_int(data.get("votos_sim")),
        to_int(data.get("votos_nao")),
        to_int(data.get("votos_abstencao")),
        bool(data.get("votacao_secreta", False)),
    )

async def upsert_voto(pool: asyncpg.Pool, **data) -> None:
    await pool.execute(
        """
        INSERT INTO votos (votacao_id, parlamentar_id, parlamentar_nome, partido, uf, voto, data_registro)
        VALUES ($1,$2,$3,$4,$5,$6,$7)
        ON CONFLICT (votacao_id, parlamentar_nome) DO UPDATE SET
            voto = EXCLUDED.voto,
            partido = EXCLUDED.partido
        """,
        data.get("votacao_id"),
        data.get("parlamentar_id"),
        normalizar_texto(data.get("parlamentar_nome"), max_len=200),
        normalizar_partido(data.get("partido")),
        normalizar_uf(data.get("uf")),
        normalizar_texto(data.get("voto"), max_len=20),
        data.get("data_registro"),
    )

async def upsert_orientacao(pool: asyncpg.Pool, **data) -> None:
    await pool.execute(
        """
        INSERT INTO orientacoes (votacao_id, partido_bloco, orientacao)
        VALUES ($1,$2,$3)
        ON CONFLICT (votacao_id, partido_bloco) DO UPDATE SET
            orientacao = EXCLUDED.orientacao
        """,
        data.get("votacao_id"),
        normalizar_texto(data.get("partido_bloco"), max_len=50),
        normalizar_texto(data.get("orientacao"), max_len=20) or "Liberado",
    )
