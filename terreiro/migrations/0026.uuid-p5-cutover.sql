-- Maracatu UUID retrofit P5 / Stage D: cut proposicoes and votacoes over to UUID PKs and
-- re-point their declared FK children to the new uuid.
-- Chain: votacoes.proposicao_id -> proposicoes ; votos.votacao_id -> votacoes ;
--        orientacoes.votacao_id -> votacoes ; plus the deferred votos.parlamentar_id -> parlamentares.
-- Prereq: 0025 backfilled votacoes.proposicao_id_uuid, votos.votacao_id_uuid,
-- orientacoes.votacao_id_uuid; 0023 (P4) backfilled votos.parlamentar_id_uuid (all NULL) and
-- 0024 (P4) dropped the votos_parlamentar_id_fkey constraint and idx_votos_parlamentar.
--
-- Steps: drop the child FK constraints; drop the two composite UNIQUE constraints that embed the
-- int votacao_id (votos(votacao_id, parlamentar_nome) and orientacoes(votacao_id, partido_bloco));
-- drop the indexes on the int FK columns; swap each child's int FK for its uuid sibling (restore
-- NOT NULL where the original was NOT NULL); swap the proposicoes and votacoes parent PKs; re-add
-- the FK constraints; rebuild the two composite UNIQUEs on the new uuid columns; recreate the
-- indexes on the new uuid columns (including idx_votos_parlamentar, dropped back in P4 / 0024).
-- yoyo runs this whole migration in a single transaction; a mid-tx failure rolls the entire
-- cutover back.
--
-- Deferred votos.parlamentar_id: it was always NULL in practice; P4 (0024) already dropped its FK
-- constraint and idx_votos_parlamentar. Here we drop the int parlamentar_id column, rename the
-- uuid sibling (added in 0023) into place, re-add the FK to parlamentares(id), and recreate
-- idx_votos_parlamentar.
--
-- Constraint auto-names confirmed against \d in the maintenance window before running:
--   votacoes_proposicao_id_fkey, votos_votacao_id_fkey, orientacoes_votacao_id_fkey,
--   votos_votacao_id_parlamentar_nome_key, orientacoes_votacao_id_partido_bloco_key,
--   proposicoes_id_uuid_key, proposicoes_pkey, votacoes_id_uuid_key, votacoes_pkey.
--
-- Polymorphic note: embeddings(tipo='votacao') and feed_eventos(referencia_tipo='votacao')
-- reference votacoes.id by integer value. After this cutover votacoes.id_uuid is renamed to id and
-- the old int id is gone, so P7's polymorphic backfill must resolve through the _uuid_xref
-- snapshot captured at P1 (0018), not by joining the live int id. See P7.
--
-- Irreversible once committed (the proposicoes/votacoes SERIAL sequences are gone):
-- see .rollback.sql.

-- Drop FK constraints pointing at proposicoes.id and votacoes.id by catalog lookup (the literal
-- names are only a guess; a truncated/hand-named FK would abort the cutover). Match contype='f' on
-- the FK column of each child.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'votacoes'
      AND con.contype = 'f'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'proposicao_id')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE votacoes DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'votos'
      AND con.contype = 'f'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'votacao_id')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE votos DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'orientacoes'
      AND con.contype = 'f'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'votacao_id')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE orientacoes DROP CONSTRAINT %I', cname);
    END IF;
END $$;

-- Drop the composite UNIQUE constraints that embed the int votacao_id (rebuilt on uuid below) by
-- catalog lookup (auto-named, truncatable). Match contype='u' on BOTH columns of each composite to
-- disambiguate from any other UNIQUE on the table.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'votos'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'votacao_id'),
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'parlamentar_nome')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE votos DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'orientacoes'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'votacao_id'),
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'partido_bloco')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE orientacoes DROP CONSTRAINT %I', cname);
    END IF;
END $$;

-- Drop the indexes on the int FK columns.
DROP INDEX IF EXISTS idx_votacoes_proposicao;
DROP INDEX IF EXISTS idx_votos_votacao;
DROP INDEX IF EXISTS idx_orientacoes_votacao;

-- Swap votacoes.proposicao_id (nullable, 0010:26) int -> uuid. Nullable: no NOT NULL to restore.
ALTER TABLE votacoes DROP COLUMN proposicao_id;
ALTER TABLE votacoes RENAME COLUMN proposicao_id_uuid TO proposicao_id;

-- Swap votos.votacao_id (was NOT NULL, 0010:48) int -> uuid; restore NOT NULL.
ALTER TABLE votos DROP COLUMN votacao_id;
ALTER TABLE votos RENAME COLUMN votacao_id_uuid TO votacao_id;
ALTER TABLE votos ALTER COLUMN votacao_id SET NOT NULL;

-- Swap votos.parlamentar_id (deferred from P4; nullable, 0010:49, always NULL) int -> uuid.
ALTER TABLE votos DROP COLUMN parlamentar_id;
ALTER TABLE votos RENAME COLUMN parlamentar_id_uuid TO parlamentar_id;

-- Swap orientacoes.votacao_id (was NOT NULL, 0010:64) int -> uuid; restore NOT NULL.
ALTER TABLE orientacoes DROP COLUMN votacao_id;
ALTER TABLE orientacoes RENAME COLUMN votacao_id_uuid TO votacao_id;
ALTER TABLE orientacoes ALTER COLUMN votacao_id SET NOT NULL;

-- Swap the proposicoes parent PK: drop the Stage-A unique, drop the int PK + int id, rename
-- id_uuid -> id, add the UUID PK. Keeps proposicoes.id_externo UNIQUE NOT NULL (0010:5), the
-- tipo/ano/casa indexes, and the search_vector GENERATED column (0011) untouched.
-- Drop the auto-named Stage-A unique (0018) on id_uuid and the int PK by catalog lookup. The
-- id_uuid attnum match disambiguates the Stage-A unique from the id_externo UNIQUE.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'proposicoes'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'id_uuid')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE proposicoes DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'proposicoes' AND con.contype = 'p';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE proposicoes DROP CONSTRAINT %I', cname);
    END IF;
END $$;
ALTER TABLE proposicoes DROP COLUMN id;
ALTER TABLE proposicoes RENAME COLUMN id_uuid TO id;
ALTER TABLE proposicoes ADD PRIMARY KEY (id);

-- Swap the votacoes parent PK (it is also the parent of votos and orientacoes, already re-pointed
-- above). Keeps votacoes.id_externo UNIQUE NOT NULL (0010:24), the casa/data/tipo indexes, and the
-- search_vector GENERATED column (0011) untouched.
-- Drop the auto-named Stage-A unique on id_uuid and the int PK by catalog lookup. The id_uuid
-- attnum match disambiguates the Stage-A unique from the id_externo UNIQUE.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'votacoes'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'id_uuid')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE votacoes DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'votacoes' AND con.contype = 'p';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE votacoes DROP CONSTRAINT %I', cname);
    END IF;
END $$;
ALTER TABLE votacoes DROP COLUMN id;
ALTER TABLE votacoes RENAME COLUMN id_uuid TO id;
ALTER TABLE votacoes ADD PRIMARY KEY (id);

-- Re-add the FK constraints on the new uuid columns (original names, no ON DELETE on any).
ALTER TABLE votacoes ADD CONSTRAINT votacoes_proposicao_id_fkey FOREIGN KEY (proposicao_id) REFERENCES proposicoes(id);
ALTER TABLE votos ADD CONSTRAINT votos_votacao_id_fkey FOREIGN KEY (votacao_id) REFERENCES votacoes(id);
ALTER TABLE votos ADD CONSTRAINT votos_parlamentar_id_fkey FOREIGN KEY (parlamentar_id) REFERENCES parlamentares(id);
ALTER TABLE orientacoes ADD CONSTRAINT orientacoes_votacao_id_fkey FOREIGN KEY (votacao_id) REFERENCES votacoes(id);

-- Rebuild the two composite UNIQUE constraints on the new uuid votacao_id (original names).
ALTER TABLE votos ADD CONSTRAINT votos_votacao_id_parlamentar_nome_key UNIQUE (votacao_id, parlamentar_nome);
ALTER TABLE orientacoes ADD CONSTRAINT orientacoes_votacao_id_partido_bloco_key UNIQUE (votacao_id, partido_bloco);

-- Recreate the indexes on the new uuid FK columns. idx_votos_parlamentar was dropped in P4 (0024)
-- and is recreated here on the uuid parlamentar_id. Keeps idx_votos_voto (0010:60) untouched.
CREATE INDEX idx_votacoes_proposicao ON votacoes(proposicao_id);
CREATE INDEX idx_votos_votacao ON votos(votacao_id);
CREATE INDEX idx_orientacoes_votacao ON orientacoes(votacao_id);
CREATE INDEX idx_votos_parlamentar ON votos(parlamentar_id);
