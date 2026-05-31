-- Maracatu UUID retrofit P2 / Stage D: cut over the independent leaf tables to UUID PKs.
-- Tables: glossario_termos, candidatos_tse, ingestao_log, raw_ingestao, orgaos_federais.
-- None is referenced by any FK and none references another table via id, so the cutover
-- is the plain leaf swap: drop the Stage-A unique, drop the old int PK + int id column,
-- rename id_uuid -> id, add the UUID PK. orgaos_federais is special-cased (no int id;
-- its PK is on codigo, which we keep UNIQUE NOT NULL for the alias-lookup in tools.py).
-- yoyo runs this whole migration in a single transaction; if any step fails the entire
-- cutover rolls back automatically. Irreversible once committed (the SERIAL sequences are
-- gone): see the .rollback.sql for the recovery procedure.

-- glossario_termos: SERIAL int id -> UUID. Keeps termo UNIQUE, embedding, idx_glossario_*.
-- Drop the auto-named Stage-A unique (0018) on id_uuid and the int PK by catalog lookup so a
-- truncated/hand-named constraint cannot abort the cutover (the literal name is only a guess).
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'glossario_termos'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'id_uuid')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE glossario_termos DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'glossario_termos' AND con.contype = 'p';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE glossario_termos DROP CONSTRAINT %I', cname);
    END IF;
END $$;
ALTER TABLE glossario_termos DROP COLUMN id;
ALTER TABLE glossario_termos RENAME COLUMN id_uuid TO id;
ALTER TABLE glossario_termos ADD PRIMARY KEY (id);

-- candidatos_tse: SERIAL int id -> UUID. Keeps its natural-key UNIQUE and indexes.
-- Drop the auto-named Stage-A unique on id_uuid and the int PK by catalog lookup.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'candidatos_tse'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'id_uuid')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE candidatos_tse DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'candidatos_tse' AND con.contype = 'p';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE candidatos_tse DROP CONSTRAINT %I', cname);
    END IF;
END $$;
ALTER TABLE candidatos_tse DROP COLUMN id;
ALTER TABLE candidatos_tse RENAME COLUMN id_uuid TO id;
ALTER TABLE candidatos_tse ADD PRIMARY KEY (id);

-- ingestao_log: SERIAL int id -> UUID. Audit table, no inbound references.
-- Drop the auto-named Stage-A unique on id_uuid and the int PK by catalog lookup.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'ingestao_log'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'id_uuid')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE ingestao_log DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'ingestao_log' AND con.contype = 'p';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE ingestao_log DROP CONSTRAINT %I', cname);
    END IF;
END $$;
ALTER TABLE ingestao_log DROP COLUMN id;
ALTER TABLE ingestao_log RENAME COLUMN id_uuid TO id;
ALTER TABLE ingestao_log ADD PRIMARY KEY (id);

-- raw_ingestao: BIGSERIAL int id -> UUID. Keeps idx_raw_dedup (unique hash_payload) and
-- idx_raw_fonte_tipo; both are on non-id columns and are untouched by the id swap.
-- Drop the auto-named Stage-A unique on id_uuid and the int PK by catalog lookup.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'raw_ingestao'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'id_uuid')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE raw_ingestao DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'raw_ingestao' AND con.contype = 'p';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE raw_ingestao DROP CONSTRAINT %I', cname);
    END IF;
END $$;
ALTER TABLE raw_ingestao DROP COLUMN id;
ALTER TABLE raw_ingestao RENAME COLUMN id_uuid TO id;
ALTER TABLE raw_ingestao ADD PRIMARY KEY (id);

-- orgaos_federais: natural PK on codigo VARCHAR(10). There is no int id column. Demote the
-- codigo PK to a plain UNIQUE NOT NULL (codigo stays the alias-lookup key in tools.py) and
-- promote id_uuid to the new UUID PK. Keeps idx_orgaos_federais_nome_oficial_lower and
-- idx_orgaos_federais_aliases_gin (both on non-id columns).
-- Drop the auto-named Stage-A unique on id_uuid and the codigo PK by catalog lookup.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'orgaos_federais'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'id_uuid')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE orgaos_federais DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'orgaos_federais' AND con.contype = 'p';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE orgaos_federais DROP CONSTRAINT %I', cname);
    END IF;
END $$;
ALTER TABLE orgaos_federais ADD CONSTRAINT orgaos_federais_codigo_key UNIQUE (codigo);
ALTER TABLE orgaos_federais ALTER COLUMN codigo SET NOT NULL;
ALTER TABLE orgaos_federais RENAME COLUMN id_uuid TO id;
ALTER TABLE orgaos_federais ADD PRIMARY KEY (id);
