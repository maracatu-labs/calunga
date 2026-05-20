
ALTER TABLE contratos DROP COLUMN IF EXISTS search_vector;
ALTER TABLE licitacoes DROP COLUMN IF EXISTS search_vector;
ALTER TABLE emendas DROP COLUMN IF EXISTS search_vector;
ALTER TABLE votacoes DROP COLUMN IF EXISTS search_vector;
ALTER TABLE proposicoes DROP COLUMN IF EXISTS search_vector;

DROP INDEX IF EXISTS idx_contratos_fts;
DROP INDEX IF EXISTS idx_licitacoes_fts;
DROP INDEX IF EXISTS idx_emendas_fts;
DROP INDEX IF EXISTS idx_votacoes_fts;
DROP INDEX IF EXISTS idx_proposicoes_fts;
