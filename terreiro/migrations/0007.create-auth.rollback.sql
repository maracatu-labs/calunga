
ALTER TABLE conversas DROP COLUMN IF EXISTS user_id;
DROP INDEX IF EXISTS idx_magic_links_email;
DROP TABLE IF EXISTS magic_links;
DROP TABLE IF EXISTS users;
