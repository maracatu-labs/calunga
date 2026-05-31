-- Rollback Maracatu UUID retrofit P5 / Stage B (proposicoes/votacoes/votos/orientacoes uuid FK backfill).
-- Fully reversible: this stage only ADDED the sibling uuid FK columns and populated them from a
-- snapshot join. Dropping them restores the post-0024 shape (the int proposicao_id/votacao_id
-- columns were never touched). No data loss: the int FK values still hold the source of truth.
-- votos.parlamentar_id_uuid is owned by P4 (0023) and is not dropped here.

ALTER TABLE votacoes DROP COLUMN IF EXISTS proposicao_id_uuid;
ALTER TABLE votos DROP COLUMN IF EXISTS votacao_id_uuid;
ALTER TABLE orientacoes DROP COLUMN IF EXISTS votacao_id_uuid;
