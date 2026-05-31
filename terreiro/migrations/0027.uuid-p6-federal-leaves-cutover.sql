-- Maracatu UUID retrofit P6 / Stage D: cut over the federal leaf tables to UUID PKs.
-- Tables: cpgf, despesas_orcamentarias, contratos, licitacoes, viagens, emendas.
-- All six are referenced ONLY polymorphically by embeddings (tipos cpgf, contrato,
-- licitacao, viagem, emenda) and feed_eventos (emenda) via an integer referencia_id +
-- discriminator, with NO declared FK in either direction. So the cutover is the plain
-- leaf swap (same shape as P2 / 0019): drop the Stage-A unique, drop the old int PK + int
-- id column, rename id_uuid -> id, add the UUID PK. No FK constraint, composite UNIQUE, or
-- inbound declared FK touches these ids, so nothing else has to be dropped or rebuilt here.
-- yoyo runs this whole migration in a single transaction; if any step fails the entire
-- cutover rolls back automatically. Irreversible once committed (the SERIAL sequences are
-- gone): see the .rollback.sql for the recovery procedure.
--
-- Each table keeps its id_externo UNIQUE NOT NULL (the ON CONFLICT upsert target), all of
-- its idx_* indexes (orgao/fornecedor/ano/etc.), and the search_vector GENERATED columns +
-- GIN indexes on contratos/licitacoes/emendas. None of those reference the id column, so
-- the id swap leaves them untouched.
--
-- Ordering vs P7: this migration runs BEFORE 0028 (P7). P7's polymorphic Stage C backfill
-- resolves int referencia_id -> uuid through the _uuid_xref snapshot captured at P1 (0018),
-- which already holds the int->uuid mapping for cpgf/contratos/licitacoes/emendas/viagens,
-- so it stays correct even though this cutover drops the live int ids.

-- cpgf: SERIAL int id -> UUID. Keeps id_externo UNIQUE and its orgao/ano/portador indexes.
-- Drop the auto-named Stage-A unique (0018) on id_uuid and the int PK by catalog lookup so a
-- truncated/hand-named constraint cannot abort the cutover (the literal name is only a guess).
-- The id_uuid attnum match disambiguates the Stage-A unique from the id_externo UNIQUE.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'cpgf'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'id_uuid')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE cpgf DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'cpgf' AND con.contype = 'p';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE cpgf DROP CONSTRAINT %I', cname);
    END IF;
END $$;
ALTER TABLE cpgf DROP COLUMN id;
ALTER TABLE cpgf RENAME COLUMN id_uuid TO id;
ALTER TABLE cpgf ADD PRIMARY KEY (id);

-- despesas_orcamentarias: SERIAL int id -> UUID. Keeps id_externo UNIQUE and its indexes.
-- Drop the auto-named Stage-A unique on id_uuid and the int PK by catalog lookup.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'despesas_orcamentarias'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'id_uuid')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE despesas_orcamentarias DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'despesas_orcamentarias' AND con.contype = 'p';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE despesas_orcamentarias DROP CONSTRAINT %I', cname);
    END IF;
END $$;
ALTER TABLE despesas_orcamentarias DROP COLUMN id;
ALTER TABLE despesas_orcamentarias RENAME COLUMN id_uuid TO id;
ALTER TABLE despesas_orcamentarias ADD PRIMARY KEY (id);

-- contratos: SERIAL int id -> UUID. Keeps id_externo UNIQUE, its indexes, and the
-- search_vector GENERATED column + its GIN index (all on non-id columns).
-- Drop the auto-named Stage-A unique on id_uuid and the int PK by catalog lookup.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'contratos'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'id_uuid')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE contratos DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'contratos' AND con.contype = 'p';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE contratos DROP CONSTRAINT %I', cname);
    END IF;
END $$;
ALTER TABLE contratos DROP COLUMN id;
ALTER TABLE contratos RENAME COLUMN id_uuid TO id;
ALTER TABLE contratos ADD PRIMARY KEY (id);

-- licitacoes: SERIAL int id -> UUID. Keeps id_externo UNIQUE, its indexes, and the
-- search_vector GENERATED column + its GIN index (all on non-id columns).
-- Drop the auto-named Stage-A unique on id_uuid and the int PK by catalog lookup.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'licitacoes'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'id_uuid')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE licitacoes DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'licitacoes' AND con.contype = 'p';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE licitacoes DROP CONSTRAINT %I', cname);
    END IF;
END $$;
ALTER TABLE licitacoes DROP COLUMN id;
ALTER TABLE licitacoes RENAME COLUMN id_uuid TO id;
ALTER TABLE licitacoes ADD PRIMARY KEY (id);

-- viagens: SERIAL int id -> UUID. Keeps id_externo UNIQUE and its indexes.
-- Drop the auto-named Stage-A unique on id_uuid and the int PK by catalog lookup.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'viagens'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'id_uuid')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE viagens DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'viagens' AND con.contype = 'p';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE viagens DROP CONSTRAINT %I', cname);
    END IF;
END $$;
ALTER TABLE viagens DROP COLUMN id;
ALTER TABLE viagens RENAME COLUMN id_uuid TO id;
ALTER TABLE viagens ADD PRIMARY KEY (id);

-- emendas: SERIAL int id -> UUID. Keeps id_externo UNIQUE, its indexes, and the
-- search_vector GENERATED column + its GIN index (all on non-id columns).
-- Drop the auto-named Stage-A unique on id_uuid and the int PK by catalog lookup.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'emendas'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'id_uuid')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE emendas DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'emendas' AND con.contype = 'p';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE emendas DROP CONSTRAINT %I', cname);
    END IF;
END $$;
ALTER TABLE emendas DROP COLUMN id;
ALTER TABLE emendas RENAME COLUMN id_uuid TO id;
ALTER TABLE emendas ADD PRIMARY KEY (id);
