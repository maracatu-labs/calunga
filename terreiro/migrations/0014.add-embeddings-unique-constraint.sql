

DELETE FROM embeddings
WHERE id NOT IN (
    SELECT MAX(id)
    FROM embeddings
    GROUP BY tipo, referencia_id
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_embeddings_tipo_referencia'
    ) THEN
        ALTER TABLE embeddings
            ADD CONSTRAINT uq_embeddings_tipo_referencia UNIQUE (tipo, referencia_id);
    END IF;
END $$;
