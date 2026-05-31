-- Rollback Maracatu UUID retrofit P4 / Stage B (parlamentares/despesas/suspeitas/votos uuid FK backfill).
-- Fully reversible: this stage only ADDED the sibling uuid FK columns and populated them from a
-- snapshot join. Dropping them restores the post-0022 shape (the int parlamentar_id/despesa_id
-- columns were never touched). No data loss: the int FK values still hold the source of truth.

ALTER TABLE despesas DROP COLUMN IF EXISTS parlamentar_id_uuid;
ALTER TABLE suspeitas DROP COLUMN IF EXISTS despesa_id_uuid;
ALTER TABLE votos DROP COLUMN IF EXISTS parlamentar_id_uuid;
