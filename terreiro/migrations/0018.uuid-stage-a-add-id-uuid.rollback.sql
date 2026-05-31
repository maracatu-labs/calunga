-- Rollback Maracatu UUID retrofit P1 / Stage A.
-- Stage A is purely additive, so this fully reverses it: drop the polymorphic snapshot
-- table, then drop every id_uuid column (DROP COLUMN also removes its Stage-A UNIQUE
-- constraint). No data loss: every original int/codigo PK is untouched by this phase.

DROP TABLE IF EXISTS _uuid_xref;

-- SERIAL integer-PK tables (21)
ALTER TABLE parlamentares DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE despesas DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE empresas DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE sancoes DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE suspeitas DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE ingestao_log DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE mensagens DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE embeddings DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE candidatos_tse DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE entes DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE cpgf DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE despesas_orcamentarias DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE contratos DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE licitacoes DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE viagens DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE emendas DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE proposicoes DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE votacoes DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE orientacoes DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE feed_eventos DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE glossario_termos DROP COLUMN IF EXISTS id_uuid;

-- BIGSERIAL integer-PK tables (4)
ALTER TABLE raw_ingestao DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE dados_fiscais DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE votos DROP COLUMN IF EXISTS id_uuid;
ALTER TABLE mensagem_feedback DROP COLUMN IF EXISTS id_uuid;

-- Natural-PK table
ALTER TABLE orgaos_federais DROP COLUMN IF EXISTS id_uuid;
