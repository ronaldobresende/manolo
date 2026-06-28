-- =============================================================
-- MANOLO — Migration Fase 4: Web App
-- Rodar manualmente no Neon (painel SQL ou psql)
-- Data: Jun/2026
-- =============================================================

-- 1. Tabela de marcos (conquistas da criança)
--    Não existia antes — criada para a Fase 4
CREATE TABLE IF NOT EXISTS marcos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  crianca_id UUID REFERENCES criancas(id),
  usuario_id UUID REFERENCES usuarios(id),
  descricao TEXT NOT NULL,
  data_marco DATE NOT NULL,
  criado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_marcos_crianca_id ON marcos (crianca_id);
CREATE INDEX IF NOT EXISTS idx_marcos_data ON marcos (crianca_id, data_marco DESC);

-- 2. Autenticação web (email único + senha hash)
--    NOTA: autenticação desabilitada na Fase 4 MVP
--    Preparar colunas agora para não ter migration depois
ALTER TABLE usuarios
  ADD COLUMN IF NOT EXISTS senha_hash TEXT,
  ADD COLUMN IF NOT EXISTS email_web TEXT;

-- Criar índice único em email_web (ignorar NULLs — só cria quando preenchido)
CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_email_web
  ON usuarios (email_web)
  WHERE email_web IS NOT NULL;

-- =============================================================
-- Verificação (opcional — pode rodar depois para confirmar)
-- =============================================================
-- SELECT table_name FROM information_schema.tables
--   WHERE table_schema = 'public' AND table_name = 'marcos';
--
-- SELECT column_name, data_type FROM information_schema.columns
--   WHERE table_name = 'usuarios' AND column_name IN ('senha_hash', 'email_web');
