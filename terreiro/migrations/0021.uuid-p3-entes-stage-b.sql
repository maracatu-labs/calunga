-- Maracatu UUID retrofit P3 / Stage B: backfill the uuid FK columns on entes' children.
-- entes is the parent of two declared FK children:
--   parlamentares.ente_id INTEGER REFERENCES entes(id)            (0009:87, nullable)
--   dados_fiscais.ente_id INTEGER NOT NULL REFERENCES entes(id)   (0009:222, NOT NULL)
-- This is additive and non-destructive: add a sibling <fk>_uuid column on each child and
-- populate it from entes.id_uuid (added in 0018) by joining on the still-present int id.
-- The old int ente_id columns stay until the 0022 cutover. yoyo runs this as one
-- transaction. Re-runnable: ADD COLUMN IF NOT EXISTS guards the columns; the UPDATEs are
-- idempotent (they re-derive the same uuid from the same int join).

ALTER TABLE parlamentares ADD COLUMN IF NOT EXISTS ente_id_uuid UUID;
UPDATE parlamentares c SET ente_id_uuid = p.id_uuid FROM entes p WHERE c.ente_id = p.id;

ALTER TABLE dados_fiscais ADD COLUMN IF NOT EXISTS ente_id_uuid UUID;
UPDATE dados_fiscais c SET ente_id_uuid = p.id_uuid FROM entes p WHERE c.ente_id = p.id;
