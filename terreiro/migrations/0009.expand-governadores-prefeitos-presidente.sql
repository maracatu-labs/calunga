

CREATE TABLE IF NOT EXISTS entes (
    id SERIAL PRIMARY KEY,
    ibge_codigo VARCHAR(7) UNIQUE NOT NULL,
    nome VARCHAR(200) NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('federal', 'estado', 'municipio')),
    uf VARCHAR(2),
    capital BOOLEAN DEFAULT FALSE,
    populacao INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entes_tipo ON entes(tipo);
CREATE INDEX IF NOT EXISTS idx_entes_uf ON entes(uf);

INSERT INTO entes (ibge_codigo, nome, tipo, uf, capital) VALUES
    ('0', 'Brasil', 'federal', NULL, FALSE)
ON CONFLICT (ibge_codigo) DO NOTHING;

INSERT INTO entes (ibge_codigo, nome, tipo, uf) VALUES
    ('12', 'Acre', 'estado', 'AC'),
    ('27', 'Alagoas', 'estado', 'AL'),
    ('13', 'Amazonas', 'estado', 'AM'),
    ('16', 'Amapá', 'estado', 'AP'),
    ('29', 'Bahia', 'estado', 'BA'),
    ('23', 'Ceará', 'estado', 'CE'),
    ('53', 'Distrito Federal', 'estado', 'DF'),
    ('32', 'Espírito Santo', 'estado', 'ES'),
    ('52', 'Goiás', 'estado', 'GO'),
    ('21', 'Maranhão', 'estado', 'MA'),
    ('31', 'Minas Gerais', 'estado', 'MG'),
    ('50', 'Mato Grosso do Sul', 'estado', 'MS'),
    ('51', 'Mato Grosso', 'estado', 'MT'),
    ('15', 'Pará', 'estado', 'PA'),
    ('25', 'Paraíba', 'estado', 'PB'),
    ('26', 'Pernambuco', 'estado', 'PE'),
    ('22', 'Piauí', 'estado', 'PI'),
    ('41', 'Paraná', 'estado', 'PR'),
    ('33', 'Rio de Janeiro', 'estado', 'RJ'),
    ('24', 'Rio Grande do Norte', 'estado', 'RN'),
    ('11', 'Rondônia', 'estado', 'RO'),
    ('14', 'Roraima', 'estado', 'RR'),
    ('43', 'Rio Grande do Sul', 'estado', 'RS'),
    ('42', 'Santa Catarina', 'estado', 'SC'),
    ('28', 'Sergipe', 'estado', 'SE'),
    ('35', 'São Paulo', 'estado', 'SP'),
    ('17', 'Tocantins', 'estado', 'TO')
ON CONFLICT (ibge_codigo) DO NOTHING;

INSERT INTO entes (ibge_codigo, nome, tipo, uf, capital) VALUES
    ('1200401', 'Rio Branco', 'municipio', 'AC', TRUE),
    ('2704302', 'Maceió', 'municipio', 'AL', TRUE),
    ('1302603', 'Manaus', 'municipio', 'AM', TRUE),
    ('1600303', 'Macapá', 'municipio', 'AP', TRUE),
    ('2927408', 'Salvador', 'municipio', 'BA', TRUE),
    ('2304400', 'Fortaleza', 'municipio', 'CE', TRUE),
    ('5300108', 'Brasília', 'municipio', 'DF', TRUE),
    ('3205309', 'Vitória', 'municipio', 'ES', TRUE),
    ('5208707', 'Goiânia', 'municipio', 'GO', TRUE),
    ('2111300', 'São Luís', 'municipio', 'MA', TRUE),
    ('3106200', 'Belo Horizonte', 'municipio', 'MG', TRUE),
    ('5002704', 'Campo Grande', 'municipio', 'MS', TRUE),
    ('5103403', 'Cuiabá', 'municipio', 'MT', TRUE),
    ('1501402', 'Belém', 'municipio', 'PA', TRUE),
    ('2507507', 'João Pessoa', 'municipio', 'PB', TRUE),
    ('2611606', 'Recife', 'municipio', 'PE', TRUE),
    ('2211001', 'Teresina', 'municipio', 'PI', TRUE),
    ('4106902', 'Curitiba', 'municipio', 'PR', TRUE),
    ('3304557', 'Rio de Janeiro', 'municipio', 'RJ', TRUE),
    ('2408102', 'Natal', 'municipio', 'RN', TRUE),
    ('1100205', 'Porto Velho', 'municipio', 'RO', TRUE),
    ('1400100', 'Boa Vista', 'municipio', 'RR', TRUE),
    ('4314902', 'Porto Alegre', 'municipio', 'RS', TRUE),
    ('4205407', 'Florianópolis', 'municipio', 'SC', TRUE),
    ('2800308', 'Aracaju', 'municipio', 'SE', TRUE),
    ('3550308', 'São Paulo', 'municipio', 'SP', TRUE),
    ('1721000', 'Palmas', 'municipio', 'TO', TRUE)
ON CONFLICT (ibge_codigo) DO NOTHING;

ALTER TABLE parlamentares DROP CONSTRAINT IF EXISTS parlamentares_tipo_check;
ALTER TABLE parlamentares ADD CONSTRAINT parlamentares_tipo_check
    CHECK (tipo IN ('deputado', 'senador', 'governador', 'prefeito', 'presidente'));

ALTER TABLE parlamentares ADD COLUMN IF NOT EXISTS esfera VARCHAR(10)
    CHECK (esfera IN ('federal', 'estadual', 'municipal'));
ALTER TABLE parlamentares ADD COLUMN IF NOT EXISTS ente_id INTEGER REFERENCES entes(id);

UPDATE parlamentares SET esfera = 'federal' WHERE esfera IS NULL;

CREATE TABLE IF NOT EXISTS cpgf (
    id SERIAL PRIMARY KEY,
    id_externo VARCHAR(200) UNIQUE,
    orgao_codigo VARCHAR(10),
    orgao_nome VARCHAR(200),
    unidade_gestora_codigo VARCHAR(10),
    unidade_gestora_nome VARCHAR(200),
    portador_nome VARCHAR(200),
    portador_cpf VARCHAR(11),
    tipo_cartao VARCHAR(50),
    transacao VARCHAR(200),
    cnpj_cpf_favorecido VARCHAR(14),
    favorecido_nome VARCHAR(200),
    valor DECIMAL(12,2),
    data_transacao DATE,
    mes_extrato SMALLINT,
    ano_extrato SMALLINT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cpgf_orgao ON cpgf(orgao_codigo);
CREATE INDEX IF NOT EXISTS idx_cpgf_portador ON cpgf(portador_cpf);
CREATE INDEX IF NOT EXISTS idx_cpgf_favorecido ON cpgf(cnpj_cpf_favorecido);
CREATE INDEX IF NOT EXISTS idx_cpgf_ano_mes ON cpgf(ano_extrato, mes_extrato);

CREATE TABLE IF NOT EXISTS despesas_orcamentarias (
    id SERIAL PRIMARY KEY,
    id_externo VARCHAR(200) UNIQUE,
    ano SMALLINT NOT NULL CHECK (ano BETWEEN 2000 AND 2100),
    orgao_superior_codigo VARCHAR(10),
    orgao_superior_nome VARCHAR(200),
    orgao_vinculado_codigo VARCHAR(10),
    orgao_vinculado_nome VARCHAR(200),
    unidade_gestora_codigo VARCHAR(10),
    unidade_gestora_nome VARCHAR(200),
    funcao VARCHAR(100),
    subfuncao VARCHAR(100),
    programa VARCHAR(200),
    acao VARCHAR(200),
    categoria_economica VARCHAR(100),
    grupo_despesa VARCHAR(100),
    elemento_despesa VARCHAR(200),
    modalidade_licitacao VARCHAR(100),
    favorecido_nome VARCHAR(300),
    favorecido_cnpj_cpf VARCHAR(14),
    valor_empenhado DECIMAL(15,2),
    valor_liquidado DECIMAL(15,2),
    valor_pago DECIMAL(15,2),
    valor_resto_pago DECIMAL(15,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_desp_orc_orgao ON despesas_orcamentarias(orgao_superior_codigo);
CREATE INDEX IF NOT EXISTS idx_desp_orc_ano ON despesas_orcamentarias(ano);
CREATE INDEX IF NOT EXISTS idx_desp_orc_favorecido ON despesas_orcamentarias(favorecido_cnpj_cpf);
CREATE INDEX IF NOT EXISTS idx_desp_orc_funcao ON despesas_orcamentarias(funcao);

CREATE TABLE IF NOT EXISTS contratos (
    id SERIAL PRIMARY KEY,
    id_externo VARCHAR(200) UNIQUE,
    orgao_codigo VARCHAR(10),
    orgao_nome VARCHAR(200),
    unidade_gestora_codigo VARCHAR(10),
    unidade_gestora_nome VARCHAR(200),
    fornecedor_nome VARCHAR(300),
    fornecedor_cnpj_cpf VARCHAR(14),
    objeto TEXT,
    numero VARCHAR(50),
    modalidade_licitacao VARCHAR(100),
    situacao VARCHAR(50),
    valor_inicial DECIMAL(15,2),
    valor_final DECIMAL(15,2),
    valor_acumulado DECIMAL(15,2),
    data_inicio DATE,
    data_fim DATE,
    data_publicacao DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_contratos_orgao ON contratos(orgao_codigo);
CREATE INDEX IF NOT EXISTS idx_contratos_fornecedor ON contratos(fornecedor_cnpj_cpf);
CREATE INDEX IF NOT EXISTS idx_contratos_situacao ON contratos(situacao);

CREATE TABLE IF NOT EXISTS licitacoes (
    id SERIAL PRIMARY KEY,
    id_externo VARCHAR(200) UNIQUE,
    orgao_codigo VARCHAR(10),
    orgao_nome VARCHAR(200),
    unidade_gestora_codigo VARCHAR(10),
    unidade_gestora_nome VARCHAR(200),
    modalidade VARCHAR(100),
    numero VARCHAR(50),
    objeto TEXT,
    situacao VARCHAR(50),
    valor_estimado DECIMAL(15,2),
    valor_homologado DECIMAL(15,2),
    data_abertura DATE,
    data_resultado DATE,
    data_publicacao DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_licitacoes_orgao ON licitacoes(orgao_codigo);
CREATE INDEX IF NOT EXISTS idx_licitacoes_modalidade ON licitacoes(modalidade);
CREATE INDEX IF NOT EXISTS idx_licitacoes_situacao ON licitacoes(situacao);

CREATE TABLE IF NOT EXISTS viagens (
    id SERIAL PRIMARY KEY,
    id_externo VARCHAR(200) UNIQUE,
    orgao_codigo VARCHAR(10),
    orgao_nome VARCHAR(200),
    viajante_nome VARCHAR(200),
    viajante_cpf VARCHAR(11),
    cargo VARCHAR(200),
    destino VARCHAR(200),
    motivo TEXT,
    urgente BOOLEAN DEFAULT FALSE,
    data_ida DATE,
    data_volta DATE,
    valor_passagens DECIMAL(12,2),
    valor_diarias DECIMAL(12,2),
    valor_outros DECIMAL(12,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_viagens_orgao ON viagens(orgao_codigo);
CREATE INDEX IF NOT EXISTS idx_viagens_viajante ON viagens(viajante_cpf);
CREATE INDEX IF NOT EXISTS idx_viagens_data ON viagens(data_ida);

CREATE TABLE IF NOT EXISTS dados_fiscais (
    id BIGSERIAL PRIMARY KEY,
    ente_id INTEGER NOT NULL REFERENCES entes(id),
    exercicio SMALLINT NOT NULL CHECK (exercicio BETWEEN 2000 AND 2100),
    periodo SMALLINT NOT NULL,
    demonstrativo VARCHAR(10) NOT NULL CHECK (demonstrativo IN ('RREO', 'RGF', 'DCA')),
    anexo VARCHAR(100) NOT NULL,
    coluna VARCHAR(200),
    rotulo VARCHAR(500),
    valor DECIMAL(20,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (ente_id, exercicio, periodo, demonstrativo, anexo, coluna, rotulo)
);

CREATE INDEX IF NOT EXISTS idx_fiscal_ente ON dados_fiscais(ente_id);
CREATE INDEX IF NOT EXISTS idx_fiscal_exercicio ON dados_fiscais(exercicio);
CREATE INDEX IF NOT EXISTS idx_fiscal_demo ON dados_fiscais(demonstrativo);

CREATE TABLE IF NOT EXISTS emendas (
    id SERIAL PRIMARY KEY,
    id_externo VARCHAR(200) UNIQUE,
    ano SMALLINT NOT NULL CHECK (ano BETWEEN 2000 AND 2100),
    autor VARCHAR(200),
    tipo_emenda VARCHAR(50),
    numero VARCHAR(20),
    localidade_gasto VARCHAR(200),
    funcao VARCHAR(100),
    subfuncao VARCHAR(100),
    valor_empenhado DECIMAL(15,2),
    valor_liquidado DECIMAL(15,2),
    valor_pago DECIMAL(15,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_emendas_ano ON emendas(ano);
CREATE INDEX IF NOT EXISTS idx_emendas_autor ON emendas(autor);
