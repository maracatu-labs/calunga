-- Maracatu UUID retrofit P4 / Stage D: cut parlamentares and despesas over to UUID PKs and
-- re-point their declared FK children to the new uuid.
-- Chain: despesas.parlamentar_id -> parlamentares ; suspeitas.despesa_id -> despesas.
-- Prereq: 0023 backfilled despesas.parlamentar_id_uuid, suspeitas.despesa_id_uuid,
-- votos.parlamentar_id_uuid.
--
-- Steps: drop the child FK constraints (despesas->parlamentares, suspeitas->despesas, and the
-- votos->parlamentares FK so parlamentares' int id can be dropped); drop the indexes on the int
-- FK columns; swap each child's int FK for its uuid sibling (restore NOT NULL where the original
-- was NOT NULL via 0008); swap the parlamentares and despesas parent PKs; re-add the FK
-- constraints; recreate the indexes on the new uuid columns. yoyo runs this whole migration in a
-- single transaction; a mid-tx failure rolls the entire cutover back.
--
-- Deferred votos handling: votos.parlamentar_id is always NULL in practice and votos itself
-- cuts over in P5 (0026). Here we only DROP the votos_parlamentar_id_fkey constraint (a prereq
-- for dropping parlamentares.id) and DROP idx_votos_parlamentar. The int votos.parlamentar_id
-- column and its uuid sibling stay untouched; P5 (0026) drops the int column, renames the uuid
-- sibling, re-adds the FK to parlamentares(id), and recreates idx_votos_parlamentar.
--
-- Polymorphic note: embeddings(tipo='despesa') and feed_eventos(referencia_tipo='despesa')
-- reference despesas.id by integer value. After this cutover despesas.id_uuid is renamed to id
-- and the old int id is gone, so P7's polymorphic backfill must resolve through the _uuid_xref
-- snapshot captured at P1 (0018), not by joining the live int id. See P7.
--
-- Irreversible once committed (the parlamentares/despesas SERIAL sequences are gone):
-- see .rollback.sql.

-- Drop FK constraints pointing at parlamentares.id and despesas.id by catalog lookup (the literal
-- names are only a guess; a truncated/hand-named FK would abort the cutover). Match contype='f' on
-- the FK column of each child. votos keeps its int parlamentar_id col until P5 (0026).
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'despesas'
      AND con.contype = 'f'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'parlamentar_id')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE despesas DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'suspeitas'
      AND con.contype = 'f'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'despesa_id')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE suspeitas DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'votos'
      AND con.contype = 'f'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'parlamentar_id')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE votos DROP CONSTRAINT %I', cname);
    END IF;
END $$;

-- Drop the indexes on the int FK columns.
DROP INDEX IF EXISTS idx_despesas_parlamentar;
DROP INDEX IF EXISTS idx_suspeitas_despesa;
DROP INDEX IF EXISTS idx_votos_parlamentar;

-- Swap despesas.parlamentar_id (was NOT NULL via 0008:18) int -> uuid; restore NOT NULL.
ALTER TABLE despesas DROP COLUMN parlamentar_id;
ALTER TABLE despesas RENAME COLUMN parlamentar_id_uuid TO parlamentar_id;
ALTER TABLE despesas ALTER COLUMN parlamentar_id SET NOT NULL;

-- Swap suspeitas.despesa_id (was NOT NULL via 0008:39) int -> uuid; restore NOT NULL.
ALTER TABLE suspeitas DROP COLUMN despesa_id;
ALTER TABLE suspeitas RENAME COLUMN despesa_id_uuid TO despesa_id;
ALTER TABLE suspeitas ALTER COLUMN despesa_id SET NOT NULL;

-- Swap the parlamentares parent PK: drop the Stage-A unique, drop the int PK + int id, rename
-- id_uuid -> id, add the UUID PK. Keeps parlamentares.id_externo UNIQUE NOT NULL (0001:7) and the
-- chk_parlamentares_uf / chk_parlamentares_partido checks (0008) untouched.
-- Drop the auto-named Stage-A unique (0018) on id_uuid and the int PK by catalog lookup. The
-- id_uuid attnum match disambiguates the Stage-A unique from the id_externo UNIQUE.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'parlamentares'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'id_uuid')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE parlamentares DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'parlamentares' AND con.contype = 'p';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE parlamentares DROP CONSTRAINT %I', cname);
    END IF;
END $$;
ALTER TABLE parlamentares DROP COLUMN id;
ALTER TABLE parlamentares RENAME COLUMN id_uuid TO id;
ALTER TABLE parlamentares ADD PRIMARY KEY (id);

-- Swap the despesas parent PK (it is also the parent of suspeitas, already re-pointed above).
-- Keeps despesas.id_externo UNIQUE (0001:25), the ano_mes/cnpj/categoria indexes, the
-- search_vector GENERATED column + idx_despesas_fts, and the chk_despesas_* checks untouched.
-- Drop the auto-named Stage-A unique on id_uuid and the int PK by catalog lookup. The id_uuid
-- attnum match disambiguates the Stage-A unique from the id_externo UNIQUE.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'despesas'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'id_uuid')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE despesas DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'despesas' AND con.contype = 'p';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE despesas DROP CONSTRAINT %I', cname);
    END IF;
END $$;
ALTER TABLE despesas DROP COLUMN id;
ALTER TABLE despesas RENAME COLUMN id_uuid TO id;
ALTER TABLE despesas ADD PRIMARY KEY (id);

-- Re-add the FK constraints on the new uuid columns (original names, no ON DELETE on either).
ALTER TABLE despesas ADD CONSTRAINT despesas_parlamentar_id_fkey FOREIGN KEY (parlamentar_id) REFERENCES parlamentares(id);
ALTER TABLE suspeitas ADD CONSTRAINT suspeitas_despesa_id_fkey FOREIGN KEY (despesa_id) REFERENCES despesas(id);
-- votos.parlamentar_id stays int + unconstrained until P5 (0026), which re-adds its FK.

-- Recreate the indexes on the new uuid FK columns. Keeps idx_suspeitas_classificador and
-- idx_suspeitas_prob (on non-id columns) untouched.
CREATE INDEX idx_despesas_parlamentar ON despesas(parlamentar_id);
CREATE INDEX idx_suspeitas_despesa ON suspeitas(despesa_id);
