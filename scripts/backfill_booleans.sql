-- Este script limpa os 'False' que foram inseridos incorretamente pelo agente no passado
-- convertendo-os de volta para NULL ('Não informado'), permitindo que os novos resumos não alucinem problemas.
-- ATENÇÃO: Isso removerá os "Não" legítimos (ex: mãe dizendo "ele não comeu bem"). 
-- Rode apenas se os benefícios de limpar o histórico compensarem a perda desses "Nãos" explícitos.

UPDATE checklist_alimentacao SET comeu_bem = NULL WHERE comeu_bem = FALSE;
UPDATE checklist_alimentacao SET comeu_sentado = NULL WHERE comeu_sentado = FALSE;

UPDATE checklist_comunicacao SET usou_gestos = NULL WHERE usou_gestos = FALSE;
UPDATE checklist_comunicacao SET apontou = NULL WHERE apontou = FALSE;
UPDATE checklist_comunicacao SET imitou = NULL WHERE imitou = FALSE;

UPDATE checklist_brincar SET fez_faz_de_conta = NULL WHERE fez_faz_de_conta = FALSE;

UPDATE checklist_higiene SET escovou_dentes = NULL WHERE escovou_dentes = FALSE;
UPDATE checklist_higiene SET sinalizou_banheiro = NULL WHERE sinalizou_banheiro = FALSE;

UPDATE checklist_vestuario SET colaborou_roupa = NULL WHERE colaborou_roupa = FALSE;
UPDATE checklist_vestuario SET incomodo_sensorial = NULL WHERE incomodo_sensorial = FALSE;

UPDATE checklist_movimento SET caiu_muito = NULL WHERE caiu_muito = FALSE;
UPDATE checklist_movimento SET buscou_colo = NULL WHERE buscou_colo = FALSE;

UPDATE checklist_humor SET teve_crise = NULL WHERE teve_crise = FALSE;

UPDATE checklist_rotina SET guardou_brinquedos = NULL WHERE guardou_brinquedos = FALSE;
UPDATE checklist_rotina SET ajudou_tarefa = NULL WHERE ajudou_tarefa = FALSE;
UPDATE checklist_rotina SET aceitou_transicao = NULL WHERE aceitou_transicao = FALSE;
UPDATE checklist_rotina SET teve_escola = NULL WHERE teve_escola = FALSE;
