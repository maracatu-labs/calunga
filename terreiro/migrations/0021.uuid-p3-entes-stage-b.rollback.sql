-- Rollback Maracatu UUID retrofit P3 / Stage B (entes children uuid FK backfill).
-- Fully reversible: this stage only ADDED the sibling uuid FK columns and populated them
-- from a snapshot join. Dropping them restores the post-0018 shape (the int ente_id columns
-- were never touched). No data loss: the int ente_id values still hold the source of truth.

ALTER TABLE parlamentares DROP COLUMN IF EXISTS ente_id_uuid;
ALTER TABLE dados_fiscais DROP COLUMN IF EXISTS ente_id_uuid;
