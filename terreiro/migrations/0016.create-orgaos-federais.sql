

CREATE TABLE IF NOT EXISTS orgaos_federais (
    codigo VARCHAR(10) PRIMARY KEY,
    nome_oficial VARCHAR(200) NOT NULL,
    aliases TEXT[] NOT NULL DEFAULT '{}',
    ativo BOOLEAN NOT NULL DEFAULT true,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orgaos_federais_nome_oficial_lower
    ON orgaos_federais (LOWER(nome_oficial));

CREATE INDEX IF NOT EXISTS idx_orgaos_federais_aliases_gin
    ON orgaos_federais USING GIN (aliases);

INSERT INTO orgaos_federais (codigo, nome_oficial, aliases) VALUES
(
    '20000',
    'Presidência da República',
    ARRAY['planalto', 'palácio do planalto', 'presidencia', 'presidência', 'pr', 'palacio do planalto']
),
(
    '20101',
    'Casa Civil da Presidência da República',
    ARRAY['casa civil', 'cc']
),
(
    '20119',
    'Gabinete de Segurança Institucional',
    ARRAY['gsi', 'gabinete de seguranca institucional', 'gabinete de segurança']
),
(
    '20202',
    'Advocacia-Geral da União',
    ARRAY['agu', 'advocacia geral da uniao', 'advocacia geral']
),
(
    '22000',
    'Ministério da Agricultura e Pecuária',
    ARRAY['mapa', 'ministerio da agricultura', 'ministério da agricultura', 'agricultura']
),
(
    '24000',
    'Ministério da Ciência, Tecnologia e Inovação',
    ARRAY['mcti', 'ministerio da ciencia e tecnologia', 'ciência e tecnologia', 'ciencia e tecnologia']
),
(
    '25000',
    'Ministério da Fazenda',
    ARRAY['fazenda', 'ministerio da fazenda', 'mf', 'ministerio da economia', 'economia']
),
(
    '26000',
    'Ministério da Educação',
    ARRAY['mec', 'ministerio da educacao', 'ministério da educação', 'educacao', 'educação']
),
(
    '28000',
    'Ministério da Justiça e Segurança Pública',
    ARRAY['mjsp', 'mj', 'ministerio da justica', 'ministério da justiça', 'justica', 'justiça']
),
(
    '30000',
    'Ministério da Previdência Social',
    ARRAY['mps', 'previdencia', 'previdência', 'ministerio da previdencia']
),
(
    '33000',
    'Ministério das Relações Exteriores',
    ARRAY['itamaraty', 'mre', 'ministerio das relacoes exteriores', 'relações exteriores', 'relacoes exteriores']
),
(
    '35000',
    'Ministério da Saúde',
    ARRAY['ms', 'saude', 'saúde', 'ministerio da saude', 'ministério da saúde']
),
(
    '36000',
    'Ministério do Trabalho e Emprego',
    ARRAY['mte', 'trabalho', 'ministerio do trabalho']
),
(
    '39000',
    'Ministério das Comunicações',
    ARRAY['mcom', 'comunicacoes', 'comunicações']
),
(
    '41000',
    'Ministério da Cultura',
    ARRAY['minc', 'cultura', 'ministerio da cultura']
),
(
    '44000',
    'Ministério do Meio Ambiente e Mudança do Clima',
    ARRAY['mma', 'meio ambiente', 'ministerio do meio ambiente']
),
(
    '51000',
    'Ministério do Esporte',
    ARRAY['me-esporte', 'esporte', 'ministerio do esporte']
),
(
    '52000',
    'Ministério da Defesa',
    ARRAY['md', 'defesa', 'ministerio da defesa']
),
(
    '53000',
    'Ministério da Integração e do Desenvolvimento Regional',
    ARRAY['midr', 'integracao nacional', 'integração nacional']
),
(
    '54000',
    'Ministério do Turismo',
    ARRAY['mtur', 'turismo']
),
(
    '55000',
    'Ministério do Desenvolvimento e Assistência Social, Família e Combate à Fome',
    ARRAY['mds', 'desenvolvimento social', 'assistencia social', 'combate a fome']
),
(
    '56000',
    'Ministério das Cidades',
    ARRAY['mcidades', 'cidades']
),
(
    '63000',
    'Controladoria-Geral da União',
    ARRAY['cgu', 'controladoria geral', 'controladoria-geral']
),
(
    '71000',
    'Ministério da Gestão e da Inovação em Serviços Públicos',
    ARRAY['mgi', 'gestao', 'gestão']
)
ON CONFLICT (codigo) DO NOTHING;
