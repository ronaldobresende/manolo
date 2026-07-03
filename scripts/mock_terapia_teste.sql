-- Este script insere uma Sessão de Terapia falsa usando os dados exatos extraídos 
-- pelo test_llm.py, para que você possa testar o visual no painel Web.

DO $$
DECLARE
    v_crianca_id UUID;
    v_usuario_id UUID;
    v_data DATE := '2026-07-02'; -- Data do log testado mais cedo
BEGIN
    -- 1. Pegar IDs padrão (piloto)
    SELECT id INTO v_crianca_id FROM criancas LIMIT 1;
    -- Busca a Viviane (Terapeuta) pelo nome
    SELECT id INTO v_usuario_id FROM usuarios WHERE nome ILIKE '%Viviane%' LIMIT 1;

    -- 2. Inserir a sessão de terapia na nova tabela sessoes_terapia
    INSERT INTO sessoes_terapia (
        crianca_id, 
        usuario_id, 
        data, 
        horario_inicio, 
        horario_fim, 
        especialidade, 
        notas
    ) VALUES (
        v_crianca_id,
        v_usuario_id,
        v_data,
        '14:00',
        '15:00',
        'Terapia Ocupacional e Fisio',
        'Colaborou com a troca da fralda dentro do que é possível para ele. As transições de sala e espera foram tranquilas.
Trabalhamos coordenação motora grossa com bom engajamento e equilíbrio, estimulação sensorial em bolinha de gel, com uso bimanual fazendo transferência de um pote para outro. Escalou com fortalecimento de MMSS.
A criança explorou equipamentos suspensos e já entende a hora do tchau, saindo do colo da Denise sem grudar no pescoço assim que ouviu início da música, ficando sentado na perna da terapeuta, esperando a finalização e solicitando voltar com a mãe.'
    )
    ON CONFLICT (crianca_id, data, especialidade) 
    DO UPDATE SET notas = EXCLUDED.notas;

END $$;
