

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS parlamentares (
    id SERIAL PRIMARY KEY,
    id_externo VARCHAR(20) UNIQUE NOT NULL,
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('deputado', 'senador')),
    nome VARCHAR(200) NOT NULL,
    nome_civil VARCHAR(200),
    cpf VARCHAR(11),
    partido VARCHAR(20),
    uf VARCHAR(2),
    legislatura INTEGER,
    foto_url TEXT,
    email VARCHAR(200),
    telefone VARCHAR(20),
    situacao VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS despesas (
    id SERIAL PRIMARY KEY,
    id_externo VARCHAR(200) UNIQUE,
    parlamentar_id INTEGER REFERENCES parlamentares(id),
    ano SMALLINT NOT NULL,
    mes SMALLINT NOT NULL,
    data_emissao DATE,
    categoria TEXT NOT NULL,
    subcategoria TEXT,
    fornecedor VARCHAR(200),
    cnpj_cpf VARCHAR(14),
    documento VARCHAR(200),
    valor_documento DECIMAL(12,2),
    valor_glosa DECIMAL(12,2) DEFAULT 0,
    valor_liquido DECIMAL(12,2),
    url_documento TEXT,
    lote INTEGER,
    ressarcimento INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_despesas_parlamentar ON despesas(parlamentar_id);
CREATE INDEX IF NOT EXISTS idx_despesas_ano_mes ON despesas(ano, mes);
CREATE INDEX IF NOT EXISTS idx_despesas_cnpj ON despesas(cnpj_cpf);
CREATE INDEX IF NOT EXISTS idx_despesas_categoria ON despesas(categoria);

CREATE TABLE IF NOT EXISTS empresas (
    id SERIAL PRIMARY KEY,
    cnpj VARCHAR(14) UNIQUE NOT NULL,
    razao_social VARCHAR(300),
    nome_fantasia VARCHAR(300),
    situacao_cadastral VARCHAR(50),
    data_situacao DATE,
    natureza_juridica VARCHAR(100),
    atividade_principal_codigo VARCHAR(10),
    atividade_principal_descricao VARCHAR(200),
    logradouro VARCHAR(200),
    municipio VARCHAR(100),
    uf VARCHAR(2),
    cep VARCHAR(8),
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),
    porte VARCHAR(50),
    capital_social DECIMAL(15,2),
    data_abertura DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sancoes (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('CEIS', 'CNEP', 'CEPIM')),
    cpf_cnpj VARCHAR(14),
    nome VARCHAR(300),
    orgao_sancionador VARCHAR(200),
    fundamentacao_legal TEXT,
    data_inicio DATE,
    data_fim DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sancoes_cpf_cnpj ON sancoes(cpf_cnpj);

CREATE TABLE IF NOT EXISTS suspeitas (
    id SERIAL PRIMARY KEY,
    despesa_id INTEGER REFERENCES despesas(id),
    classificador VARCHAR(50) NOT NULL,
    probabilidade DECIMAL(5,4),
    detalhes JSONB,
    verificada BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_suspeitas_despesa ON suspeitas(despesa_id);
CREATE INDEX IF NOT EXISTS idx_suspeitas_classificador ON suspeitas(classificador);
CREATE INDEX IF NOT EXISTS idx_suspeitas_prob ON suspeitas(probabilidade DESC);

CREATE TABLE IF NOT EXISTS raw_ingestao (
    id BIGSERIAL PRIMARY KEY,
    fonte VARCHAR(50) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    hash_payload VARCHAR(64) NOT NULL,
    ingerido_em TIMESTAMPTZ DEFAULT NOW(),
    processado BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_raw_fonte_tipo ON raw_ingestao(fonte, tipo, ingerido_em DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_raw_dedup ON raw_ingestao(hash_payload);

CREATE TABLE IF NOT EXISTS ingestao_log (
    id SERIAL PRIMARY KEY,
    fonte VARCHAR(50) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    registros_processados INTEGER DEFAULT 0,
    registros_novos INTEGER DEFAULT 0,
    erro TEXT,
    iniciado_em TIMESTAMPTZ DEFAULT NOW(),
    finalizado_em TIMESTAMPTZ
);
