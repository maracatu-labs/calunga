

CREATE TABLE IF NOT EXISTS feed_eventos (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(50) NOT NULL,
    categoria VARCHAR(50) NOT NULL,
    origem VARCHAR(10) NOT NULL CHECK (origem IN ('dagster', 'chat')),
    titulo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    dados JSONB,
    referencia_tipo VARCHAR(50),
    referencia_id INTEGER,
    relevancia DECIMAL(3,2) DEFAULT 0.50 CHECK (relevancia BETWEEN 0 AND 1),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (referencia_tipo, referencia_id, tipo)
);

CREATE INDEX IF NOT EXISTS idx_feed_created ON feed_eventos(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feed_tipo ON feed_eventos(tipo);
CREATE INDEX IF NOT EXISTS idx_feed_categoria ON feed_eventos(categoria);
CREATE INDEX IF NOT EXISTS idx_feed_origem ON feed_eventos(origem);
CREATE INDEX IF NOT EXISTS idx_feed_ref ON feed_eventos(referencia_tipo, referencia_id);
