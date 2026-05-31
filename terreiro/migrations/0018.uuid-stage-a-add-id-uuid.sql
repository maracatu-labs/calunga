-- Maracatu UUID retrofit P1 / Stage A: additive id_uuid on every integer-PK table.
-- Non-destructive. Adds id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid() to all
-- 25 integer-PK tables plus orgaos_federais (natural PK on codigo). Existing rows are
-- backfilled automatically by the column default at ADD COLUMN time (NOT NULL forces it).
-- gen_random_uuid() is core PostgreSQL 13+; no extension required.
-- Also snapshots the int->uuid mapping for the polymorphic parents into _uuid_xref so the
-- P7 backfill (embeddings, feed_eventos) survives after parent int ids are dropped in P2-P6.
-- The retrofit window pauses Dagster/Celery before this runs, so the snapshot is complete.

-- SERIAL integer-PK tables (21)
ALTER TABLE parlamentares ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE despesas ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE sancoes ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE suspeitas ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE ingestao_log ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE mensagens ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE embeddings ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE candidatos_tse ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE entes ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE cpgf ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE despesas_orcamentarias ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE contratos ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE licitacoes ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE viagens ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE emendas ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE proposicoes ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE votacoes ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE orientacoes ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE feed_eventos ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE glossario_termos ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();

-- BIGSERIAL integer-PK tables (4)
ALTER TABLE raw_ingestao ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE dados_fiscais ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE votos ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();
ALTER TABLE mensagem_feedback ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();

-- Natural-PK table (codigo VARCHAR): gains id_uuid now, becomes the UUID PK in P2 cutover
ALTER TABLE orgaos_federais ADD COLUMN IF NOT EXISTS id_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid();

-- Polymorphic-parent int->uuid snapshot for the P7 backfill of embeddings/feed_eventos.
-- Captured while every parent still has both its int id and id_uuid side by side.
CREATE TABLE IF NOT EXISTS _uuid_xref (
    tabela TEXT NOT NULL,
    id_int BIGINT NOT NULL,
    id_uuid UUID NOT NULL,
    PRIMARY KEY (tabela, id_int)
);

INSERT INTO _uuid_xref (tabela, id_int, id_uuid)
    SELECT 'despesas', id, id_uuid FROM despesas
  UNION ALL SELECT 'contratos', id, id_uuid FROM contratos
  UNION ALL SELECT 'licitacoes', id, id_uuid FROM licitacoes
  UNION ALL SELECT 'emendas', id, id_uuid FROM emendas
  UNION ALL SELECT 'proposicoes', id, id_uuid FROM proposicoes
  UNION ALL SELECT 'votacoes', id, id_uuid FROM votacoes
  UNION ALL SELECT 'viagens', id, id_uuid FROM viagens
  UNION ALL SELECT 'cpgf', id, id_uuid FROM cpgf
  UNION ALL SELECT 'sancoes', id, id_uuid FROM sancoes
ON CONFLICT DO NOTHING;
