

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'contratos' AND column_name = 'search_vector'
    ) THEN
        ALTER TABLE contratos ADD COLUMN search_vector tsvector
            GENERATED ALWAYS AS (
                to_tsvector('portuguese',
                    coalesce(objeto, '') || ' ' ||
                    coalesce(fornecedor_nome, '') || ' ' ||
                    coalesce(orgao_nome, '') || ' ' ||
                    coalesce(modalidade_licitacao, '')
                )
            ) STORED;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_contratos_fts ON contratos USING GIN (search_vector);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'licitacoes' AND column_name = 'search_vector'
    ) THEN
        ALTER TABLE licitacoes ADD COLUMN search_vector tsvector
            GENERATED ALWAYS AS (
                to_tsvector('portuguese',
                    coalesce(objeto, '') || ' ' ||
                    coalesce(orgao_nome, '') || ' ' ||
                    coalesce(modalidade, '')
                )
            ) STORED;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_licitacoes_fts ON licitacoes USING GIN (search_vector);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'emendas' AND column_name = 'search_vector'
    ) THEN
        ALTER TABLE emendas ADD COLUMN search_vector tsvector
            GENERATED ALWAYS AS (
                to_tsvector('portuguese',
                    coalesce(autor, '') || ' ' ||
                    coalesce(localidade_gasto, '') || ' ' ||
                    coalesce(funcao, '') || ' ' ||
                    coalesce(subfuncao, '') || ' ' ||
                    coalesce(tipo_emenda, '')
                )
            ) STORED;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_emendas_fts ON emendas USING GIN (search_vector);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'votacoes' AND column_name = 'search_vector'
    ) THEN
        ALTER TABLE votacoes ADD COLUMN search_vector tsvector
            GENERATED ALWAYS AS (
                to_tsvector('portuguese',
                    coalesce(descricao, '') || ' ' ||
                    coalesce(sigla_tipo, '') || ' ' ||
                    coalesce(orgao, '')
                )
            ) STORED;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_votacoes_fts ON votacoes USING GIN (search_vector);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'proposicoes' AND column_name = 'search_vector'
    ) THEN
        ALTER TABLE proposicoes ADD COLUMN search_vector tsvector
            GENERATED ALWAYS AS (
                to_tsvector('portuguese',
                    coalesce(ementa, '') || ' ' ||
                    coalesce(sigla_tipo, '') || ' ' ||
                    coalesce(autor, '') || ' ' ||
                    coalesce(tema, '')
                )
            ) STORED;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_proposicoes_fts ON proposicoes USING GIN (search_vector);
