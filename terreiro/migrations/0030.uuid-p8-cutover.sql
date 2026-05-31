-- Maracatu UUID retrofit P8 / Stage D: cut mensagens over to a UUID PK, re-point its declared FK
-- child (mensagem_feedback.mensagem_id), and cut mensagem_feedback's own PK over to UUID.
-- Chain: mensagem_feedback.mensagem_id -> mensagens(id) ON DELETE CASCADE (0017:5).
-- Prereq: 0029 (P8 Stage B) backfilled mensagem_feedback.mensagem_id_uuid from mensagens.id_uuid;
-- 0018 (Stage A) added id_uuid to both mensagens (SERIAL) and mensagem_feedback (BIGSERIAL).
--
-- User data: mensagem_feedback is append-only user feedback and mensagens holds conversation
-- history. Both are converted with zero data loss: only id/FK columns are reshaped; the rows, their
-- content, tool_calls, tipo/categoria/comentario, timestamps, and the already-UUID
-- mensagens.conversa_id (0002) and mensagem_feedback.user_id (0017) are untouched.
--
-- Steps (single transaction, order matters because of the cross-table FK and CASCADE):
--   1. Drop the child FK constraint and the two indexes that name the int mensagem_id.
--   2. Swap mensagem_feedback.mensagem_id int -> uuid; restore NOT NULL (original was NOT NULL).
--   3. Swap the mensagens parent PK (SERIAL int -> uuid).
--   4. Re-add the FK on the new uuid columns, PRESERVING the original ON DELETE CASCADE.
--   5. Swap mensagem_feedback's own PK (BIGSERIAL int -> uuid).
--   6. Recreate both indexes on the new uuid mensagem_id / already-uuid user_id.
-- yoyo runs this whole migration in a single transaction; a mid-tx failure rolls the entire cutover
-- back.
--
-- Constraint auto-names confirmed against \d in the maintenance window before running:
--   mensagem_feedback_mensagem_id_fkey, mensagem_feedback_id_uuid_key, mensagem_feedback_pkey,
--   mensagens_id_uuid_key, mensagens_pkey.
--
-- Irreversible once committed (the mensagens and mensagem_feedback id sequences are gone):
-- see .rollback.sql.

-- Drop the child FK constraint pointing at mensagens.id and the indexes that name int mensagem_id.
-- Resolve the FK by catalog lookup (matching contype='f' on mensagem_id) so a truncated/hand-named
-- FK cannot abort the cutover (the literal name is only a guess).
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'mensagem_feedback'
      AND con.contype = 'f'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'mensagem_id')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE mensagem_feedback DROP CONSTRAINT %I', cname);
    END IF;
END $$;
DROP INDEX IF EXISTS idx_mensagem_feedback_msg;
DROP INDEX IF EXISTS idx_mensagem_feedback_user_msg;

-- Swap mensagem_feedback.mensagem_id (was NOT NULL, 0017:5) int -> uuid; restore NOT NULL.
ALTER TABLE mensagem_feedback DROP COLUMN mensagem_id;
ALTER TABLE mensagem_feedback RENAME COLUMN mensagem_id_uuid TO mensagem_id;
ALTER TABLE mensagem_feedback ALTER COLUMN mensagem_id SET NOT NULL;

-- Swap the mensagens parent PK: drop the Stage-A unique, drop the int PK + int id, rename
-- id_uuid -> id, add the UUID PK. Keeps mensagens.conversa_id UUID FK + idx_mensagens_conversa
-- (0002) and the tool_calls/content/role/created_at columns untouched.
-- Drop the auto-named Stage-A unique (0018) on id_uuid and the int PK by catalog lookup.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'mensagens'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'id_uuid')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE mensagens DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'mensagens' AND con.contype = 'p';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE mensagens DROP CONSTRAINT %I', cname);
    END IF;
END $$;
ALTER TABLE mensagens DROP COLUMN id;
ALTER TABLE mensagens RENAME COLUMN id_uuid TO id;
ALTER TABLE mensagens ADD PRIMARY KEY (id);

-- Re-add the FK on the new uuid columns, PRESERVING the original ON DELETE CASCADE (0017:5).
ALTER TABLE mensagem_feedback ADD CONSTRAINT mensagem_feedback_mensagem_id_fkey
    FOREIGN KEY (mensagem_id) REFERENCES mensagens(id) ON DELETE CASCADE;

-- Swap mensagem_feedback's own PK (BIGSERIAL int -> uuid). Keeps mensagem_feedback.user_id UUID FK
-- (0017), the tipo/categoria/comentario CHECK + columns, and created_at untouched.
-- Drop the auto-named Stage-A unique (0018) on id_uuid and the int PK by catalog lookup.
DO $$
DECLARE
    cname TEXT;
BEGIN
    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'mensagem_feedback'
      AND con.contype = 'u'
      AND con.conkey @> ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = rel.oid AND attname = 'id_uuid')
      ]::smallint[];
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE mensagem_feedback DROP CONSTRAINT %I', cname);
    END IF;

    SELECT con.conname INTO cname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'mensagem_feedback' AND con.contype = 'p';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE mensagem_feedback DROP CONSTRAINT %I', cname);
    END IF;
END $$;
ALTER TABLE mensagem_feedback DROP COLUMN id;
ALTER TABLE mensagem_feedback RENAME COLUMN id_uuid TO id;
ALTER TABLE mensagem_feedback ADD PRIMARY KEY (id);

-- Recreate the indexes on the new uuid mensagem_id (and already-uuid user_id), matching 0017:13-14.
CREATE INDEX idx_mensagem_feedback_msg ON mensagem_feedback(mensagem_id);
CREATE INDEX idx_mensagem_feedback_user_msg ON mensagem_feedback(user_id, mensagem_id, created_at DESC);
