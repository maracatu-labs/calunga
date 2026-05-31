-- Maracatu UUID retrofit P5 / Stage B: backfill the uuid FK columns for the
-- proposicoes -> votacoes -> {votos, orientacoes} chain.
-- Declared FK children re-pointed here:
--   votacoes.proposicao_id  INTEGER REFERENCES proposicoes(id)  (0010:26, nullable)
--   votos.votacao_id        INTEGER NOT NULL REFERENCES votacoes(id)  (0010:48)
--   orientacoes.votacao_id  INTEGER NOT NULL REFERENCES votacoes(id)  (0010:64)
-- This is additive and non-destructive: add a sibling <fk>_uuid column on each child and
-- populate it from the parent's id_uuid (added in 0018) by joining on the still-present int id.
-- The old int FK columns stay until the 0026 cutover. yoyo runs this as one transaction.
-- Re-runnable: ADD COLUMN IF NOT EXISTS guards the columns; the UPDATEs are idempotent (they
-- re-derive the same uuid from the same join).
--
-- Note: votos.parlamentar_id_uuid was already added and (NULL) backfilled in P4 (0023), and
-- votos kept its int parlamentar_id column there; the votos.parlamentar_id swap + FK rebuild to
-- parlamentares(id) happens in this phase's cutover (0026). It is not repeated here.

ALTER TABLE votacoes ADD COLUMN IF NOT EXISTS proposicao_id_uuid UUID;
UPDATE votacoes c SET proposicao_id_uuid = p.id_uuid FROM proposicoes p WHERE c.proposicao_id = p.id;

ALTER TABLE votos ADD COLUMN IF NOT EXISTS votacao_id_uuid UUID;
UPDATE votos c SET votacao_id_uuid = v.id_uuid FROM votacoes v WHERE c.votacao_id = v.id;

ALTER TABLE orientacoes ADD COLUMN IF NOT EXISTS votacao_id_uuid UUID;
UPDATE orientacoes c SET votacao_id_uuid = v.id_uuid FROM votacoes v WHERE c.votacao_id = v.id;
