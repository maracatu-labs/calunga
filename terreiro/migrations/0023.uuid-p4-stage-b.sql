-- Maracatu UUID retrofit P4 / Stage B: backfill the uuid FK columns for the
-- parlamentares -> despesas -> suspeitas chain (plus the deferred votos.parlamentar_id).
-- Declared FK children re-pointed here:
--   despesas.parlamentar_id INTEGER NOT NULL REFERENCES parlamentares(id)  (0001:26, NOT NULL via 0008:18)
--   suspeitas.despesa_id   INTEGER NOT NULL REFERENCES despesas(id)        (0001:88, NOT NULL via 0008:39)
--   votos.parlamentar_id   INTEGER REFERENCES parlamentares(id)            (0010:263, nullable, always NULL in practice)
-- This is additive and non-destructive: add a sibling <fk>_uuid column on each child and
-- populate it from the parent's id_uuid (added in 0018) by joining on the still-present int id.
-- The old int FK columns stay until the 0024 cutover. votos.parlamentar_id_uuid is added and
-- backfilled here (the UPDATE matches no rows today since parlamentar_id is always NULL), but
-- votos keeps its int parlamentar_id column and its FK is rebuilt only when votos cuts over in
-- P5 (0026); 0024 just drops the votos -> parlamentares FK constraint so parlamentares' int id
-- can be dropped. yoyo runs this as one transaction. Re-runnable: ADD COLUMN IF NOT EXISTS
-- guards the columns; the UPDATEs are idempotent (they re-derive the same uuid from the same join).

ALTER TABLE despesas ADD COLUMN IF NOT EXISTS parlamentar_id_uuid UUID;
UPDATE despesas c SET parlamentar_id_uuid = p.id_uuid FROM parlamentares p WHERE c.parlamentar_id = p.id;

ALTER TABLE suspeitas ADD COLUMN IF NOT EXISTS despesa_id_uuid UUID;
UPDATE suspeitas c SET despesa_id_uuid = d.id_uuid FROM despesas d WHERE c.despesa_id = d.id;

ALTER TABLE votos ADD COLUMN IF NOT EXISTS parlamentar_id_uuid UUID;
UPDATE votos c SET parlamentar_id_uuid = p.id_uuid FROM parlamentares p WHERE c.parlamentar_id = p.id;  -- all NULL today
