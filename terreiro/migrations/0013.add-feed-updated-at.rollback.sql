

DROP INDEX IF EXISTS idx_feed_origem_tipo_created;

ALTER TABLE feed_eventos DROP COLUMN IF EXISTS updated_at;
