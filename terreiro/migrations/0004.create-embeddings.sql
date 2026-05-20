

CREATE TABLE IF NOT EXISTS embeddings (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(20) NOT NULL,
    referencia_id INTEGER NOT NULL,
    conteudo_texto TEXT NOT NULL,
    embedding vector(1024),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw ON embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 200);

CREATE INDEX IF NOT EXISTS idx_embeddings_tipo ON embeddings(tipo, referencia_id);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'despesas' AND column_name = 'search_vector'
    ) THEN
        ALTER TABLE despesas ADD COLUMN search_vector tsvector
            GENERATED ALWAYS AS (
                to_tsvector('portuguese',
                    coalesce(fornecedor, '') || ' ' ||
                    coalesce(categoria, '') || ' ' ||
                    coalesce(documento, '')
                )
            ) STORED;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_despesas_fts ON despesas USING GIN (search_vector);
