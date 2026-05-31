-- Rollback Maracatu UUID retrofit P8 / Stage B (mensagens/mensagem_feedback uuid FK backfill).
-- Fully reversible: this stage only ADDED the sibling mensagem_id_uuid column and populated it from
-- a snapshot join. Dropping it restores the post-0028 shape (the int mensagem_id column was never
-- touched). No data loss: the int FK values still hold the source of truth.

ALTER TABLE mensagem_feedback DROP COLUMN IF EXISTS mensagem_id_uuid;
