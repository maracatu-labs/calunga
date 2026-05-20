

ALTER TABLE empresas ADD COLUMN IF NOT EXISTS cnpj_basico VARCHAR(8);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS cnpj_ordem VARCHAR(4);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS cnpj_dv VARCHAR(2);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS matriz_filial VARCHAR(1);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS nome_fantasia_rf VARCHAR(300);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS motivo_situacao VARCHAR(50);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS cnae_secundaria TEXT;
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS tipo_logradouro VARCHAR(50);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS numero VARCHAR(20);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS complemento VARCHAR(200);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS bairro VARCHAR(100);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS ddd VARCHAR(4);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS telefone VARCHAR(20);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS email VARCHAR(200);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS situacao_especial VARCHAR(100);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS data_situacao_especial DATE;
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS qualificacao_responsavel VARCHAR(50);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS ente_federativo VARCHAR(100);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS fonte VARCHAR(20) DEFAULT 'bulk';

CREATE INDEX IF NOT EXISTS idx_empresas_cnpj_basico ON empresas(cnpj_basico);
CREATE INDEX IF NOT EXISTS idx_empresas_situacao ON empresas(situacao_cadastral);
CREATE INDEX IF NOT EXISTS idx_empresas_uf ON empresas(uf);
CREATE INDEX IF NOT EXISTS idx_empresas_cnae ON empresas(atividade_principal_codigo);
