-- Maracatu UUID retrofit P7 / Stage C + D: polymorphic backfill and cutover of the two
-- tables that reference their parents by an integer referencia_id + discriminator, with no
-- declared FK in either direction: embeddings and feed_eventos.
--
-- embeddings.referencia_id (INTEGER NOT NULL, 0004:6) + embeddings.tipo discriminate over the
-- federal/legislative parents {despesas, contratos, licitacoes, emendas, proposicoes, votacoes,
-- viagens, cpgf, sancoes}. feed_eventos.referencia_id (INTEGER, nullable, 0012:12) +
-- feed_eventos.referencia_tipo discriminate over {despesa, votacao, emenda}; rows with
-- referencia_tipo='empresa' carry referencia_id NULL (chat discoveries, tools.py:633) and stay NULL.
--
-- Stage C resolves each int referencia_id to the parent's uuid through the _uuid_xref snapshot
-- captured at P1 (0018), NOT by joining the parents' live int id. Every one of these parents has
-- already cut over to a UUID PK in P3-P6 (sancoes in 0020; cpgf/contratos/licitacoes/viagens/
-- emendas in 0027; despesas in 0024; proposicoes/votacoes in 0026), so their int ids no longer
-- exist. _uuid_xref still holds the int->uuid mapping for all nine, which is why P7 runs last and
-- the snapshot mechanism is mandatory. The retrofit window pauses Dagster/Celery before P1, so the
-- snapshot is complete for every row present in the window.
--
-- Stage D then cuts both tables over to their own UUID PKs and rebuilds the UNIQUE constraint and
-- index that embed referencia_id on the new uuid column. yoyo runs this whole migration in a single
-- transaction; a mid-tx failure rolls the entire backfill + cutover back automatically.
-- Irreversible once committed (the embeddings/feed_eventos SERIAL sequences are gone): see the
-- .rollback.sql for the recovery procedure.

-- ---------------------------------------------------------------------------------------------
-- Stage C: backfill the new uuid reference columns from the _uuid_xref snapshot.
-- ---------------------------------------------------------------------------------------------

-- embeddings: map every (tipo, referencia_id) to the parent uuid. referencia_id is NOT NULL, so
-- every row resolves through exactly one discriminator branch.
ALTER TABLE embeddings ADD COLUMN IF NOT EXISTS referencia_id_uuid UUID;
UPDATE embeddings e SET referencia_id_uuid = x.id_uuid
  FROM _uuid_xref x
 WHERE x.id_int = e.referencia_id
   AND x.tabela = CASE e.tipo
        WHEN 'despesa' THEN 'despesas'
        WHEN 'contrato' THEN 'contratos'
        WHEN 'licitacao' THEN 'licitacoes'
        WHEN 'emenda' THEN 'emendas'
        WHEN 'proposicao' THEN 'proposicoes'
        WHEN 'votacao' THEN 'votacoes'
        WHEN 'viagem' THEN 'viagens'
        WHEN 'cpgf' THEN 'cpgf'
        WHEN 'sancao' THEN 'sancoes'
   END;

-- feed_eventos: map only the rows that carry a referencia_id. referencia_tipo='empresa' rows have
-- referencia_id NULL (chat discoveries) and are left NULL by the IS NOT NULL guard.
ALTER TABLE feed_eventos ADD COLUMN IF NOT EXISTS referencia_id_uuid UUID;
UPDATE feed_eventos f SET referencia_id_uuid = x.id_uuid
  FROM _uuid_xref x
 WHERE f.referencia_id IS NOT NULL
   AND x.id_int = f.referencia_id
   AND x.tabela = CASE f.referencia_tipo
        WHEN 'despesa' THEN 'despesas'
        WHEN 'votacao' THEN 'votacoes'
        WHEN 'emenda' THEN 'emendas'
   END;

-- ---------------------------------------------------------------------------------------------
-- Stage D: cut embeddings over to a UUID PK and rebuild its referencia_id-bearing UNIQUE + index.
-- ---------------------------------------------------------------------------------------------

-- Drop the UNIQUE (tipo, referencia_id) (0014: uq_embeddings_tipo_referencia) and the matching
-- index (0004:16 idx_embeddings_tipo) before the int referencia_id column is removed. Resolve the
-- UNIQUE by catalog lookup (matching contype='u' on both tipo + referencia_id) rather than trusting
-- the literal name. This disambiguates it from the Stage-A unique on id_uuid.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'embeddings'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'tipo'),
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'referencia_id')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE embeddings DROP CONSTRAINT %I', cname);
    END IF;
END $$;
DROP INDEX IF EXISTS idx_embeddings_tipo;

-- Swap referencia_id (was NOT NULL via 0004:6) int -> uuid; restore NOT NULL.
ALTER TABLE embeddings DROP COLUMN referencia_id;
ALTER TABLE embeddings RENAME COLUMN referencia_id_uuid TO referencia_id;
ALTER TABLE embeddings ALTER COLUMN referencia_id SET NOT NULL;

-- Swap the embeddings own PK: drop the Stage-A unique, drop the int PK + int id, rename
-- id_uuid -> id, add the UUID PK. Keeps embedding vector(1024) + idx_embeddings_hnsw (0004:12,
-- on the embedding column) untouched.
-- Drop the auto-named Stage-A unique (0018) on id_uuid and the int PK by catalog lookup.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'embeddings'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'id_uuid')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE embeddings DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'embeddings' AND con.contype = 'p';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE embeddings DROP CONSTRAINT %I', cname);
    END IF;
END $$;
ALTER TABLE embeddings DROP COLUMN id;
ALTER TABLE embeddings RENAME COLUMN id_uuid TO id;
ALTER TABLE embeddings ADD PRIMARY KEY (id);

-- Rebuild the UNIQUE and index on the new uuid referencia_id (same names as before).
ALTER TABLE embeddings ADD CONSTRAINT uq_embeddings_tipo_referencia UNIQUE (tipo, referencia_id);
CREATE INDEX idx_embeddings_tipo ON embeddings(tipo, referencia_id);

-- ---------------------------------------------------------------------------------------------
-- Stage D: cut feed_eventos over to a UUID PK and rebuild its referencia_id-bearing UNIQUE + index.
-- ---------------------------------------------------------------------------------------------

-- Drop the UNIQUE (referencia_tipo, referencia_id, tipo) (0012:15, auto-named
-- feed_eventos_referencia_tipo_referencia_id_tipo_key, truncatable past 63 chars) and the matching
-- index (0012:22 idx_feed_ref) before the int referencia_id column is removed. Resolve the UNIQUE by
-- catalog lookup (matching contype='u' on all three columns) rather than trusting the literal name.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'feed_eventos'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'referencia_tipo'),
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'referencia_id'),
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'tipo')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE feed_eventos DROP CONSTRAINT %I', cname);
    END IF;
END $$;
DROP INDEX IF EXISTS idx_feed_ref;

-- Swap referencia_id (nullable, 0012:12) int -> uuid; keep it nullable (empresa rows stay NULL).
ALTER TABLE feed_eventos DROP COLUMN referencia_id;
ALTER TABLE feed_eventos RENAME COLUMN referencia_id_uuid TO referencia_id;

-- Swap the feed_eventos own PK: drop the Stage-A unique, drop the int PK + int id, rename
-- id_uuid -> id, add the UUID PK. Keeps idx_feed_created/idx_feed_tipo/idx_feed_categoria/
-- idx_feed_origem (and any origem_tipo_created index) untouched.
-- Drop the auto-named Stage-A unique (0018) on id_uuid and the int PK by catalog lookup.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'feed_eventos'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'id_uuid')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE feed_eventos DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'feed_eventos' AND con.contype = 'p';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE feed_eventos DROP CONSTRAINT %I', cname);
    END IF;
END $$;
ALTER TABLE feed_eventos DROP COLUMN id;
ALTER TABLE feed_eventos RENAME COLUMN id_uuid TO id;
ALTER TABLE feed_eventos ADD PRIMARY KEY (id);

-- Rebuild the UNIQUE and index on the new uuid referencia_id (same auto-name as the original so it
-- stays identical, and same index). UNIQUE keeps NULLs distinct, so the multiple
-- (empresa, NULL, empresa_sancionada) rows coexist exactly as before.
ALTER TABLE feed_eventos ADD CONSTRAINT feed_eventos_referencia_tipo_referencia_id_tipo_key UNIQUE (referencia_tipo, referencia_id, tipo);
CREATE INDEX idx_feed_ref ON feed_eventos(referencia_tipo, referencia_id);

-- ---------------------------------------------------------------------------------------------
-- Drop the int->uuid snapshot: P7 is the last consumer of _uuid_xref (created at P1 / 0018).
-- ---------------------------------------------------------------------------------------------
DROP TABLE IF EXISTS _uuid_xref;
