-- Maracatu UUID retrofit P8 / Stage B: backfill the uuid FK column for the
-- mensagens -> mensagem_feedback chain.
-- Declared FK child re-pointed here:
--   mensagem_feedback.mensagem_id  INTEGER NOT NULL REFERENCES mensagens(id) ON DELETE CASCADE
--                                  (0017:5)
-- This is additive and non-destructive: add a sibling mensagem_id_uuid column on the child and
-- populate it from the parent's id_uuid (added in 0018) by joining on the still-present int id.
-- The old int FK column stays until the 0030 cutover. yoyo runs this as one transaction.
-- Re-runnable: ADD COLUMN IF NOT EXISTS guards the column; the UPDATE is idempotent (it re-derives
-- the same uuid from the same join).
--
-- User data: mensagem_feedback rows are append-only user feedback; every row references an existing
-- mensagens row (mensagem_id is NOT NULL), so every row gets a non-NULL mensagem_id_uuid here.
-- mensagens.conversa_id (already UUID, 0002) and mensagem_feedback.user_id (already UUID, 0017) are
-- untouched.

ALTER TABLE mensagem_feedback ADD COLUMN IF NOT EXISTS mensagem_id_uuid UUID;
UPDATE mensagem_feedback c SET mensagem_id_uuid = m.id_uuid FROM mensagens m WHERE c.mensagem_id = m.id;
