

CREATE TABLE IF NOT EXISTS mensagem_feedback (
    id BIGSERIAL PRIMARY KEY,
    mensagem_id INTEGER NOT NULL REFERENCES mensagens(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('like', 'dislike')),
    categoria VARCHAR(40),
    comentario TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mensagem_feedback_msg ON mensagem_feedback(mensagem_id);
CREATE INDEX IF NOT EXISTS idx_mensagem_feedback_user_msg ON mensagem_feedback(user_id, mensagem_id, created_at DESC);
