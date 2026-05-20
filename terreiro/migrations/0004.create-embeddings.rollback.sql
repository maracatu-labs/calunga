
DROP INDEX IF EXISTS idx_despesas_fts;
ALTER TABLE despesas DROP COLUMN IF EXISTS search_vector;
DROP TABLE IF EXISTS embeddings CASCADE;
