-- Maracatu UUID retrofit P3 / Stage D: cut entes over to a UUID PK and re-point both FK
-- children (parlamentares.ente_id, dados_fiscais.ente_id) to the new uuid.
-- Prereq: 0021 backfilled parlamentares.ente_id_uuid and dados_fiscais.ente_id_uuid.
-- Steps: drop the child FK constraints + the dados_fiscais composite UNIQUE that embeds
-- ente_id + idx_fiscal_ente; swap each child's int ente_id for its uuid sibling; swap the
-- entes parent PK; re-add the FK constraints; rebuild the composite UNIQUE and index on the
-- new uuid column. dados_fiscais.ente_id was NOT NULL originally (0009:222) so NOT NULL is
-- restored; parlamentares.ente_id was nullable so it stays nullable. yoyo runs this whole
-- migration in a single transaction; a mid-tx failure rolls the entire cutover back.
-- Irreversible once committed (the entes SERIAL sequence is gone): see .rollback.sql.
--
-- The dados_fiscais composite UNIQUE (ente_id, exercicio, periodo, demonstrativo, anexo,
-- coluna, rotulo) (0009:231) is auto-named and truncated past 63 chars, so it is dropped
-- by resolving its real name from the catalog, then rebuilt with an explicit stable name.

-- Drop dependent FK constraints on entes(id) by catalog lookup (the literal names are only a
-- guess; a truncated/hand-named FK would abort the cutover). Match contype='f' on the ente_id
-- column of each child.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'parlamentares'
      AND con.contype = 'f'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'ente_id')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE parlamentares DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'dados_fiscais'
      AND con.contype = 'f'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'ente_id')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE dados_fiscais DROP CONSTRAINT %I', cname);
    END IF;
END $$;

-- Drop the dados_fiscais composite UNIQUE embedding ente_id (auto-named/truncated).
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
    WHERE rel.relname = 'dados_fiscais'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'ente_id')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE dados_fiscais DROP CONSTRAINT %I', cname);
    END IF;
END $$;

-- Drop the index on the int FK column.
DROP INDEX IF EXISTS idx_fiscal_ente;

-- Swap parlamentares.ente_id (nullable) int -> uuid.
ALTER TABLE parlamentares DROP COLUMN ente_id;
ALTER TABLE parlamentares RENAME COLUMN ente_id_uuid TO ente_id;

-- Swap dados_fiscais.ente_id (was NOT NULL via 0009) int -> uuid; restore NOT NULL.
ALTER TABLE dados_fiscais DROP COLUMN ente_id;
ALTER TABLE dados_fiscais RENAME COLUMN ente_id_uuid TO ente_id;
ALTER TABLE dados_fiscais ALTER COLUMN ente_id SET NOT NULL;

-- Swap the entes parent PK: drop the Stage-A unique, drop the int PK + int id, rename
-- id_uuid -> id, add the UUID PK. Keeps entes.ibge_codigo UNIQUE NOT NULL (0009:5) untouched.
-- Drop the auto-named Stage-A unique (0018) on id_uuid and the int PK by catalog lookup. The
-- id_uuid attnum match disambiguates the Stage-A unique from the ibge_codigo UNIQUE.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'entes'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'id_uuid')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE entes DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'entes' AND con.contype = 'p';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE entes DROP CONSTRAINT %I', cname);
    END IF;
END $$;
ALTER TABLE entes DROP COLUMN id;
ALTER TABLE entes RENAME COLUMN id_uuid TO id;
ALTER TABLE entes ADD PRIMARY KEY (id);

-- Re-add the FK constraints on the new uuid column (original names, no ON DELETE on either).
ALTER TABLE parlamentares ADD CONSTRAINT parlamentares_ente_id_fkey FOREIGN KEY (ente_id) REFERENCES entes(id);
ALTER TABLE dados_fiscais ADD CONSTRAINT dados_fiscais_ente_id_fkey FOREIGN KEY (ente_id) REFERENCES entes(id);

-- Rebuild the dados_fiscais composite UNIQUE on the new uuid ente_id (explicit stable name).
ALTER TABLE dados_fiscais ADD CONSTRAINT uq_dados_fiscais_ente_chave
    UNIQUE (ente_id, exercicio, periodo, demonstrativo, anexo, coluna, rotulo);

-- Recreate the index on the new uuid FK column.
CREATE INDEX idx_fiscal_ente ON dados_fiscais(ente_id);
