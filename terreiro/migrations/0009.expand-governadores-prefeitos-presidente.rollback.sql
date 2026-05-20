

DROP TABLE IF EXISTS emendas;
DROP TABLE IF EXISTS dados_fiscais;
DROP TABLE IF EXISTS viagens;
DROP TABLE IF EXISTS licitacoes;
DROP TABLE IF EXISTS contratos;
DROP TABLE IF EXISTS despesas_orcamentarias;
DROP TABLE IF EXISTS cpgf;

ALTER TABLE parlamentares DROP COLUMN IF EXISTS esfera;
ALTER TABLE parlamentares DROP COLUMN IF EXISTS ente_id;
ALTER TABLE parlamentares DROP CONSTRAINT IF EXISTS parlamentares_tipo_check;
ALTER TABLE parlamentares ADD CONSTRAINT parlamentares_tipo_check CHECK (tipo IN ('deputado', 'senador'));

DROP TABLE IF EXISTS entes;
