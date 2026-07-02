-- Adiciona as novas colunas de horário do cochilo
ALTER TABLE checklist_sono
ADD COLUMN cochilo_inicio TIME,
ADD COLUMN cochilo_fim TIME;

-- Remove a coluna antiga (booleana)
ALTER TABLE checklist_sono
DROP COLUMN cochilo;
