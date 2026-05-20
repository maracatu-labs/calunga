

CREATE TABLE IF NOT EXISTS candidatos_tse (
    id SERIAL PRIMARY KEY,
    ano_eleicao SMALLINT NOT NULL,
    tipo_eleicao VARCHAR(50),
    uf VARCHAR(2),
    cargo VARCHAR(50),
    numero_candidato VARCHAR(10),
    nome VARCHAR(200) NOT NULL,
    nome_urna VARCHAR(200),
    cpf VARCHAR(11),
    cnpj_campanha VARCHAR(14),
    partido VARCHAR(20),
    situacao VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tse_cnpj ON candidatos_tse(cnpj_campanha);
CREATE INDEX IF NOT EXISTS idx_tse_cpf ON candidatos_tse(cpf);
CREATE INDEX IF NOT EXISTS idx_tse_nome ON candidatos_tse(nome);
