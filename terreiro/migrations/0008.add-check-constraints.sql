

DO $$ BEGIN
    ALTER TABLE despesas ADD CONSTRAINT chk_despesas_mes CHECK (mes BETWEEN 0 AND 12);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE despesas ADD CONSTRAINT chk_despesas_ano CHECK (ano BETWEEN 2000 AND 2100);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE despesas ADD CONSTRAINT chk_despesas_glosa_positiva CHECK (valor_glosa >= 0);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

ALTER TABLE despesas ALTER COLUMN parlamentar_id SET NOT NULL;

DO $$ BEGIN
    ALTER TABLE parlamentares ADD CONSTRAINT chk_parlamentares_uf
        CHECK (uf IS NULL OR uf ~ '^[A-Z]{2}$');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

UPDATE parlamentares SET partido = UPPER(partido) WHERE partido != UPPER(partido);

DO $$ BEGIN
    ALTER TABLE parlamentares ADD CONSTRAINT chk_parlamentares_partido
        CHECK (partido IS NULL OR partido = UPPER(partido));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE suspeitas ADD CONSTRAINT chk_suspeitas_prob CHECK (probabilidade BETWEEN 0 AND 1);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

ALTER TABLE suspeitas ALTER COLUMN despesa_id SET NOT NULL;

DO $$ BEGIN
    ALTER TABLE sancoes ADD CONSTRAINT chk_sancoes_doc_digits
        CHECK (cpf_cnpj IS NULL OR cpf_cnpj ~ '^\d+$');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
