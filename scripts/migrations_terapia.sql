-- Adiciona a coluna teve_escola caso não exista
ALTER TABLE checklist_rotina ADD COLUMN IF NOT EXISTS teve_escola BOOLEAN;

-- Criação da tabela sessoes_terapia com concatenação prevista (UNIQUE em crianca_id, data, especialidade)
CREATE TABLE IF NOT EXISTS sessoes_terapia (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    crianca_id UUID REFERENCES criancas(id),
    usuario_id UUID REFERENCES usuarios(id),
    data DATE NOT NULL,
    horario_inicio TIME,
    horario_fim TIME,
    especialidade TEXT DEFAULT 'Geral',
    notas TEXT,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (crianca_id, data, especialidade)
);
