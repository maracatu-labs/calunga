

CREATE TABLE IF NOT EXISTS proposicoes (
    id SERIAL PRIMARY KEY,
    id_externo VARCHAR(50) UNIQUE NOT NULL,
    casa VARCHAR(10) NOT NULL CHECK (casa IN ('camara', 'senado')),
    sigla_tipo VARCHAR(10) NOT NULL,
    numero INTEGER NOT NULL,
    ano SMALLINT NOT NULL CHECK (ano BETWEEN 1988 AND 2100),
    ementa TEXT,
    data_apresentacao DATE,
    autor VARCHAR(300),
    tema VARCHAR(200),
    url_inteiro_teor TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_proposicoes_tipo ON proposicoes(sigla_tipo);
CREATE INDEX IF NOT EXISTS idx_proposicoes_ano ON proposicoes(ano);
CREATE INDEX IF NOT EXISTS idx_proposicoes_casa ON proposicoes(casa);

CREATE TABLE IF NOT EXISTS votacoes (
    id SERIAL PRIMARY KEY,
    id_externo VARCHAR(100) UNIQUE NOT NULL,
    casa VARCHAR(10) NOT NULL CHECK (casa IN ('camara', 'senado')),
    proposicao_id INTEGER REFERENCES proposicoes(id),
    sigla_tipo VARCHAR(10),
    numero INTEGER,
    ano SMALLINT,
    descricao TEXT,
    data_hora TIMESTAMPTZ NOT NULL,
    orgao VARCHAR(50),
    aprovada BOOLEAN,
    votos_sim INTEGER,
    votos_nao INTEGER,
    votos_abstencao INTEGER,
    votacao_secreta BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_votacoes_casa ON votacoes(casa);
CREATE INDEX IF NOT EXISTS idx_votacoes_data ON votacoes(data_hora DESC);
CREATE INDEX IF NOT EXISTS idx_votacoes_tipo ON votacoes(sigla_tipo);
CREATE INDEX IF NOT EXISTS idx_votacoes_proposicao ON votacoes(proposicao_id);

CREATE TABLE IF NOT EXISTS votos (
    id BIGSERIAL PRIMARY KEY,
    votacao_id INTEGER NOT NULL REFERENCES votacoes(id),
    parlamentar_id INTEGER REFERENCES parlamentares(id),
    parlamentar_nome VARCHAR(200) NOT NULL,
    partido VARCHAR(20),
    uf VARCHAR(2),
    voto VARCHAR(20) NOT NULL,
    data_registro TIMESTAMPTZ,
    UNIQUE (votacao_id, parlamentar_nome)
);

CREATE INDEX IF NOT EXISTS idx_votos_votacao ON votos(votacao_id);
CREATE INDEX IF NOT EXISTS idx_votos_parlamentar ON votos(parlamentar_id);
CREATE INDEX IF NOT EXISTS idx_votos_voto ON votos(voto);

CREATE TABLE IF NOT EXISTS orientacoes (
    id SERIAL PRIMARY KEY,
    votacao_id INTEGER NOT NULL REFERENCES votacoes(id),
    partido_bloco VARCHAR(50) NOT NULL,
    orientacao VARCHAR(20) NOT NULL,
    UNIQUE (votacao_id, partido_bloco)
);

CREATE INDEX IF NOT EXISTS idx_orientacoes_votacao ON orientacoes(votacao_id);
