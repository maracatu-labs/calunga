

ALTER TABLE despesas DROP CONSTRAINT IF EXISTS chk_despesas_mes;
ALTER TABLE despesas DROP CONSTRAINT IF EXISTS chk_despesas_ano;
ALTER TABLE despesas DROP CONSTRAINT IF EXISTS chk_despesas_glosa_positiva;
ALTER TABLE despesas ALTER COLUMN parlamentar_id DROP NOT NULL;
ALTER TABLE parlamentares DROP CONSTRAINT IF EXISTS chk_parlamentares_uf;
ALTER TABLE parlamentares DROP CONSTRAINT IF EXISTS chk_parlamentares_partido;
ALTER TABLE suspeitas DROP CONSTRAINT IF EXISTS chk_suspeitas_prob;
ALTER TABLE suspeitas ALTER COLUMN despesa_id DROP NOT NULL;
ALTER TABLE sancoes DROP CONSTRAINT IF EXISTS chk_sancoes_doc_digits;
