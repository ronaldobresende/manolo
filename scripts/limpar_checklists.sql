-- Limpar tabelas filhas primeiro (pois não há ON DELETE CASCADE)
DELETE FROM checklist_sono;
DELETE FROM checklist_alimentacao;
DELETE FROM checklist_brincar;
DELETE FROM checklist_comunicacao;
DELETE FROM checklist_higiene;
DELETE FROM checklist_humor;
DELETE FROM checklist_movimento;
DELETE FROM checklist_rotina;
DELETE FROM checklist_tela;
DELETE FROM checklist_vestuario;
DELETE FROM checklist_sinais_alerta;

-- Limpar tabela pai
DELETE FROM checklists;

-- (Opcional) Você pode rodar isso via Python:
-- import psycopg2
-- from core.config import settings
-- conn = psycopg2.connect(settings.DATABASE_URL)
-- cur = conn.cursor()
-- cur.execute(open("scripts/limpar_checklists.sql").read())
-- conn.commit()
