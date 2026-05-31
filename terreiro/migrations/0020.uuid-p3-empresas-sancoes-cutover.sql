-- Maracatu UUID retrofit P3 / Stage D: cut over the independent leaf tables empresas and
-- sancoes to UUID PKs.
-- Neither has a declared FK: sancoes joins empresas by cpf_cnpj = cnpj text (feed.py:163,
-- tools.py:559), not by id, so there is no FK to drop or rebuild here. Each is a plain leaf
-- swap: drop the Stage-A unique, drop the old int PK + int id column, rename id_uuid -> id,
-- add the UUID PK. yoyo runs this whole migration in a single transaction; if any step
-- fails the entire cutover rolls back automatically. Irreversible once committed (the
-- SERIAL sequences are gone): see the .rollback.sql for the recovery procedure.
--
-- Ordering note: sancoes.id IS referenced polymorphically by embeddings (tipo='sancao').
-- That backfill is P7 and joins through the _uuid_xref snapshot captured in 0018 (which
-- recorded sancoes' old int id -> id_uuid while both still existed), so dropping the int id
-- here is safe. empresas.id is referenced by nothing (chat feed events use referencia_id=NULL).

-- empresas: SERIAL int id -> UUID. Keeps cnpj UNIQUE NOT NULL (0001:51) and all 0003 indexes.
-- Drop the auto-named Stage-A unique (0018) on id_uuid and the int PK by catalog lookup so a
-- truncated/hand-named constraint cannot abort the cutover (the literal name is only a guess).
-- The id_uuid attnum match disambiguates the Stage-A unique from the cnpj UNIQUE.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'empresas'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'id_uuid')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE empresas DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'empresas' AND con.contype = 'p';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE empresas DROP CONSTRAINT %I', cname);
    END IF;
END $$;
ALTER TABLE empresas DROP COLUMN id;
ALTER TABLE empresas RENAME COLUMN id_uuid TO id;
ALTER TABLE empresas ADD PRIMARY KEY (id);

-- sancoes: SERIAL int id -> UUID. Keeps idx_sancoes_cpf_cnpj (0001:84) and
-- chk_sancoes_doc_digits (0008:42); both are on non-id columns and survive the id swap.
-- Drop the auto-named Stage-A unique on id_uuid and the int PK by catalog lookup.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'sancoes'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'id_uuid')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE sancoes DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'sancoes' AND con.contype = 'p';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE sancoes DROP CONSTRAINT %I', cname);
    END IF;
END $$;
ALTER TABLE sancoes DROP COLUMN id;
ALTER TABLE sancoes RENAME COLUMN id_uuid TO id;
ALTER TABLE sancoes ADD PRIMARY KEY (id);
