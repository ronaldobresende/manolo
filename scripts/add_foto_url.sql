-- Adiciona a coluna foto_url na tabela criancas
ALTER TABLE criancas ADD COLUMN IF NOT EXISTS foto_url VARCHAR(500);
