-- ==============================================================================
-- MIGRATION: TRANSFORMAR ALIMENTAÇÃO, COMUNICAÇÃO E SONO EM EVENTOS (1-PARA-N)
-- ==============================================================================

-- 1. CRIAÇÃO DAS NOVAS TABELAS DE EVENTOS
-- ==========================================

-- Tabela de Eventos de Alimentação
CREATE TABLE checklist_alimentacao_eventos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  checklist_id UUID REFERENCES checklists(id) ON DELETE CASCADE,
  horario TIME,
  tipo_refeicao TEXT CHECK (tipo_refeicao IN ('cafe_manha', 'lanche', 'almoco', 'jantar', 'livre')),
  aceitou TEXT[] DEFAULT '{}',
  recusou TEXT[] DEFAULT '{}',
  comeu_bem BOOLEAN,
  comeu_sentado BOOLEAN,
  utensilio TEXT CHECK (utensilio IN ('colher', 'garfo', 'mao', 'misto')),
  notas TEXT,
  criado_em TIMESTAMPTZ DEFAULT NOW()
);

-- Tabela de Eventos de Comunicação
CREATE TABLE checklist_comunicacao_eventos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  checklist_id UUID REFERENCES checklists(id) ON DELETE CASCADE,
  horario TIME,
  contexto TEXT,
  palavras_ditas TEXT[] DEFAULT '{}',
  tipo_emissao TEXT CHECK (tipo_emissao IN ('espontanea', 'imitacao', 'tentativa', 'gesto_isolado')),
  notas TEXT,
  criado_em TIMESTAMPTZ DEFAULT NOW()
);

-- Tabela de Eventos de Sono
CREATE TABLE checklist_sono_eventos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  checklist_id UUID REFERENCES checklists(id) ON DELETE CASCADE,
  horario_inicio TIME,
  horario_fim TIME,
  tipo TEXT CHECK (tipo IN ('noturno', 'cochilo', 'despertar_noturno')),
  notas TEXT,
  criado_em TIMESTAMPTZ DEFAULT NOW()
);


-- 2. MIGRAÇÃO DE DADOS (Preservar Histórico)
-- ==========================================
-- Pegamos o registro consolidado do dia antigo e transformamos em 1 evento genérico

-- Migrar Alimentação
INSERT INTO checklist_alimentacao_eventos (checklist_id, aceitou, recusou, comeu_bem, comeu_sentado, utensilio, notas)
SELECT checklist_id, aceitou, recusou, comeu_bem, comeu_sentado, utensilio, 'Dado migrado do modelo antigo'
FROM checklist_alimentacao;

-- Migrar Comunicação (Convertendo lógicas antigas)
INSERT INTO checklist_comunicacao_eventos (checklist_id, palavras_ditas, tipo_emissao, notas)
SELECT 
    checklist_id, 
    palavras_ditas, 
    CASE WHEN imitou = TRUE THEN 'imitacao' ELSE 'espontanea' END,
    'Migrado. Usou gestos: ' || COALESCE(usou_gestos::text, 'null') || 
    ' | Apontou: ' || COALESCE(apontou::text, 'null') || 
    ' | Puxou mão: ' || COALESCE(puxou_mao, 'null')
FROM checklist_comunicacao;

-- Migrar Sono (Noturno e Cochilos como eventos separados)
-- Primeiro os sonos noturnos
INSERT INTO checklist_sono_eventos (checklist_id, horario_inicio, horario_fim, tipo, notas)
SELECT checklist_id, dormiu_as, acordou_as, 'noturno', notas
FROM checklist_sono 
WHERE dormiu_as IS NOT NULL OR acordou_as IS NOT NULL;

-- Depois os cochilos
INSERT INTO checklist_sono_eventos (checklist_id, tipo, notas)
SELECT checklist_id, 'cochilo', 'Cochilou durante o dia (horário não registrado no modelo antigo)'
FROM checklist_sono 
WHERE cochilo = TRUE;


-- 3. REMOÇÃO DAS TABELAS ANTIGAS (Limpeza)
-- ==========================================
-- Descomente estas linhas APÓS rodar os INSERTS acima e verificar se deu tudo certo.
/*
DROP TABLE checklist_alimentacao;
DROP TABLE checklist_comunicacao;
DROP TABLE checklist_sono;
*/