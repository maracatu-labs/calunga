

ALTER TABLE feed_eventos
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

UPDATE feed_eventos SET updated_at = created_at WHERE updated_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_feed_origem_tipo_created
    ON feed_eventos (origem, tipo, created_at DESC);
