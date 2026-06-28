"""Estruturação e preenchimento do checklist diário.

Responsável por salvar dados parciais de rotina e consultar campos ausentes para cobrança conversacional.
"""

import logging
import json
from datetime import date, timedelta
from core.database import get_connection

logger = logging.getLogger(__name__)

# Ordem de prioridade para cobrança conversacional (PROMPT B4)
PRIORIDADE_CAMPOS = [
    "sono", "humor", "comunicacao", "alimentacao",
    "brincar", "higiene", "movimento", "vestuario", "tela", "rotina"
]

# Mapeamento campo → tabela e pergunta natural para cobrança
CAMPO_CONFIG = {
    "sono": {
        "tabela": "checklist_sono",
        "pergunta": "Como foi o sono {da_crianca} {periodo}? Dormiu bem, acordou à noite?",
    },
    "humor": {
        "tabela": "checklist_humor",
        "pergunta": "Como esteve o humor {da_crianca} {periodo}? Teve alguma crise ou ficou mais tranquilo?",
    },
    "comunicacao": {
        "tabela": "checklist_comunicacao",
        "pergunta": "E a comunicação {da_crianca} {periodo}? Usou algum gesto, palavra nova ou apontou para algo?",
    },
    "alimentacao": {
        "tabela": "checklist_alimentacao",
        "pergunta": "Como foi a alimentação {da_crianca} {periodo}? Comeu bem, aceitou algo novo?",
    },
    "brincar": {
        "tabela": "checklist_brincar",
        "pergunta": "Com o que {a_crianca} brincou {periodo}? Brincou sozinho ou com alguém?",
    },
    "higiene": {
        "tabela": "checklist_higiene",
        "pergunta": "Como foi o banho e a higiene {da_crianca} {periodo}? Tranquilo ou teve resistência?",
    },
    "movimento": {
        "tabela": "checklist_movimento",
        "pergunta": "{a_crianca} fez alguma atividade de movimento {periodo}? Correu, pulou, brincou no parquinho?",
    },
    "vestuario": {
        "tabela": "checklist_vestuario",
        "pergunta": "E na hora de vestir {periodo}, {a_crianca} colaborou ou teve algum incômodo?",
    },
    "tela": {
        "tabela": "checklist_tela",
        "pergunta": "{a_crianca} usou tela {periodo}? Se sim, por quanto tempo e como reagiu ao tirar?",
    },
    "rotina": {
        "tabela": "checklist_rotina",
        "pergunta": "Como {a_crianca} lidou com as transições de atividade {periodo}? Guardou brinquedos, ajudou em algo?",
    },
}


def _obter_ou_criar_checklist(crianca_id: str, usuario_id: str, data: str, origem: str) -> str:
    """Obtém o ID do checklist do dia ou cria um novo. Retorna o checklist_id."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO checklists (crianca_id, usuario_id, data, origem)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (crianca_id, data) DO UPDATE
                SET origem = EXCLUDED.origem
                RETURNING id
            """, (crianca_id, usuario_id, data, origem))
            checklist_id = cur.fetchone()['id']
        conn.commit()
    return str(checklist_id)


def salvar_checklist(crianca_id: str, usuario_id: str, data: str, origem: str, analise_json: str):
    """
    Lê o JSON estruturado (Pydantic mode='json') e persiste nas tabelas relacionais exatas.
    """
    try:
        dados = json.loads(analise_json)
        campos = dados.get("campos_preenchidos", {})

        with get_connection() as conn:
            with conn.cursor() as cur:
                # 1. Tabela raiz: checklists (Cria ou atualiza para a data)
                cur.execute("""
                    INSERT INTO checklists (crianca_id, usuario_id, data, origem)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (crianca_id, data) DO UPDATE 
                    SET origem = EXCLUDED.origem
                    RETURNING id
                """, (crianca_id, usuario_id, data, origem))
                checklist_id = cur.fetchone()['id']

                # 2. Salvar cada seção
                _upsert_campos_no_banco(cur, checklist_id, campos)
                
            conn.commit()
        logger.info(f"Checklist salvo com sucesso nas tabelas relacionais! (Checklist ID: {checklist_id})")
        return checklist_id
    except Exception as e:
        logger.error(f"Erro ao salvar checklist: {e}")
        return None


def salvar_campo_individual(checklist_id: str, campo: str, dados: dict):
    """
    Salva um campo individual do checklist (usado para respostas a cobranças).
    """
    try:
        config = CAMPO_CONFIG.get(campo)
        if not config:
            logger.warning(f"Campo '{campo}' não reconhecido.")
            return False

        with get_connection() as conn:
            with conn.cursor() as cur:
                campos = {campo: dados}
                _upsert_campos_no_banco(cur, checklist_id, campos)
            conn.commit()
        logger.info(f"Campo '{campo}' salvo com sucesso no checklist {checklist_id}.")
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar campo individual '{campo}': {e}")
        return False


def _upsert_campos_no_banco(cur, checklist_id: str, campos: dict):
    """Lógica unificada para inserir ou atualizar campos tipados do Pydantic no banco."""
    
    # Utilitário para limpar quebras de linha indesejadas no notas
    def _clean_notas(old, new):
        if old and old.strip():
            return old + '\n' + (new or '')
        return new or None

    # SONO
    if "sono" in campos and campos["sono"]:
        s = campos["sono"]
        cur.execute("""
            INSERT INTO checklist_sono (checklist_id, dormiu_as, acordou_as, acordou_noite, cochilo, notas)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (checklist_id) DO UPDATE SET 
            dormiu_as = COALESCE(EXCLUDED.dormiu_as, checklist_sono.dormiu_as),
            acordou_as = COALESCE(EXCLUDED.acordou_as, checklist_sono.acordou_as),
            acordou_noite = COALESCE(EXCLUDED.acordou_noite, checklist_sono.acordou_noite),
            cochilo = COALESCE(EXCLUDED.cochilo, checklist_sono.cochilo),
            notas = CASE 
                WHEN checklist_sono.notas IS NOT NULL AND checklist_sono.notas != '' AND EXCLUDED.notas IS NOT NULL THEN checklist_sono.notas || E'\n' || EXCLUDED.notas
                ELSE COALESCE(EXCLUDED.notas, checklist_sono.notas)
            END
        """, (checklist_id, s.get('dormiu_as'), s.get('acordou_as'), s.get('acordou_noite'), s.get('cochilo'), s.get('notas')))

    # TELA
    if "tela" in campos and campos["tela"]:
        t = campos["tela"]
        cur.execute("""
            INSERT INTO checklist_tela (checklist_id, usou_tela, tempo_minutos, conteudo, reacao_retirada)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (checklist_id) DO UPDATE SET 
            usou_tela = COALESCE(EXCLUDED.usou_tela, checklist_tela.usou_tela),
            tempo_minutos = COALESCE(EXCLUDED.tempo_minutos, checklist_tela.tempo_minutos),
            conteudo = COALESCE(EXCLUDED.conteudo, checklist_tela.conteudo),
            reacao_retirada = COALESCE(EXCLUDED.reacao_retirada, checklist_tela.reacao_retirada)
        """, (checklist_id, t.get('usou_tela'), t.get('tempo_minutos'), t.get('conteudo'), t.get('reacao_retirada')))

    # ALIMENTACAO
    if "alimentacao" in campos and campos["alimentacao"]:
        a = campos["alimentacao"]
        cur.execute("""
            INSERT INTO checklist_alimentacao (checklist_id, comeu_bem, aceitou, recusou, comeu_sentado, utensilio)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (checklist_id) DO UPDATE SET 
            comeu_bem = COALESCE(EXCLUDED.comeu_bem, checklist_alimentacao.comeu_bem),
            aceitou = EXCLUDED.aceitou,
            recusou = EXCLUDED.recusou,
            comeu_sentado = COALESCE(EXCLUDED.comeu_sentado, checklist_alimentacao.comeu_sentado),
            utensilio = COALESCE(EXCLUDED.utensilio, checklist_alimentacao.utensilio)
        """, (checklist_id, a.get('comeu_bem'), a.get('aceitou'), a.get('recusou'), a.get('comeu_sentado'), a.get('utensilio')))

    # COMUNICACAO
    if "comunicacao" in campos and campos["comunicacao"]:
        c = campos["comunicacao"]
        cur.execute("""
            INSERT INTO checklist_comunicacao (checklist_id, usou_gestos, palavras_ditas, apontou, puxou_mao, respondeu_nome, imitou)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (checklist_id) DO UPDATE SET 
            usou_gestos = COALESCE(EXCLUDED.usou_gestos, checklist_comunicacao.usou_gestos),
            palavras_ditas = EXCLUDED.palavras_ditas,
            apontou = COALESCE(EXCLUDED.apontou, checklist_comunicacao.apontou),
            puxou_mao = COALESCE(EXCLUDED.puxou_mao, checklist_comunicacao.puxou_mao),
            respondeu_nome = COALESCE(EXCLUDED.respondeu_nome, checklist_comunicacao.respondeu_nome),
            imitou = COALESCE(EXCLUDED.imitou, checklist_comunicacao.imitou)
        """, (checklist_id, c.get('usou_gestos'), c.get('palavras_ditas'), c.get('apontou'), c.get('puxou_mao'), c.get('respondeu_nome'), c.get('imitou')))

    # BRINCAR
    if "brincar" in campos and campos["brincar"]:
        b = campos["brincar"]
        cur.execute("""
            INSERT INTO checklist_brincar (checklist_id, com_que_brincou, modo, fez_faz_de_conta, tempo_sem_tela_minutos)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (checklist_id) DO UPDATE SET 
            com_que_brincou = EXCLUDED.com_que_brincou,
            modo = COALESCE(EXCLUDED.modo, checklist_brincar.modo),
            fez_faz_de_conta = COALESCE(EXCLUDED.fez_faz_de_conta, checklist_brincar.fez_faz_de_conta),
            tempo_sem_tela_minutos = COALESCE(EXCLUDED.tempo_sem_tela_minutos, checklist_brincar.tempo_sem_tela_minutos)
        """, (checklist_id, b.get('com_que_brincou'), b.get('modo'), b.get('fez_faz_de_conta'), b.get('tempo_sem_tela_minutos')))

    # HIGIENE
    if "higiene" in campos and campos["higiene"]:
        h = campos["higiene"]
        cur.execute("""
            INSERT INTO checklist_higiene (checklist_id, banho, escovou_dentes, sinalizou_banheiro)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (checklist_id) DO UPDATE SET 
            banho = COALESCE(EXCLUDED.banho, checklist_higiene.banho),
            escovou_dentes = COALESCE(EXCLUDED.escovou_dentes, checklist_higiene.escovou_dentes),
            sinalizou_banheiro = COALESCE(EXCLUDED.sinalizou_banheiro, checklist_higiene.sinalizou_banheiro)
        """, (checklist_id, h.get('banho'), h.get('escovou_dentes'), h.get('sinalizou_banheiro')))

    # VESTUARIO
    if "vestuario" in campos and campos["vestuario"]:
        v = campos["vestuario"]
        cur.execute("""
            INSERT INTO checklist_vestuario (checklist_id, colaborou_roupa, incomodo_sensorial)
            VALUES (%s, %s, %s)
            ON CONFLICT (checklist_id) DO UPDATE SET 
            colaborou_roupa = COALESCE(EXCLUDED.colaborou_roupa, checklist_vestuario.colaborou_roupa),
            incomodo_sensorial = COALESCE(EXCLUDED.incomodo_sensorial, checklist_vestuario.incomodo_sensorial)
        """, (checklist_id, v.get('colaborou_roupa'), v.get('incomodo_sensorial')))

    # MOVIMENTO
    if "movimento" in campos and campos["movimento"]:
        m = campos["movimento"]
        cur.execute("""
            INSERT INTO checklist_movimento (checklist_id, atividades, caiu_muito, buscou_colo)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (checklist_id) DO UPDATE SET 
            atividades = EXCLUDED.atividades,
            caiu_muito = COALESCE(EXCLUDED.caiu_muito, checklist_movimento.caiu_muito),
            buscou_colo = COALESCE(EXCLUDED.buscou_colo, checklist_movimento.buscou_colo)
        """, (checklist_id, m.get('atividades'), m.get('caiu_muito'), m.get('buscou_colo')))

    # HUMOR
    if "humor" in campos and campos["humor"]:
        h = campos["humor"]
        cur.execute("""
            INSERT INTO checklist_humor (checklist_id, humor_geral, teve_crise, o_que_acalmou, notas)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (checklist_id) DO UPDATE SET 
            humor_geral = COALESCE(EXCLUDED.humor_geral, checklist_humor.humor_geral),
            teve_crise = COALESCE(EXCLUDED.teve_crise, checklist_humor.teve_crise),
            o_que_acalmou = COALESCE(EXCLUDED.o_que_acalmou, checklist_humor.o_que_acalmou),
            notas = CASE 
                WHEN checklist_humor.notas IS NOT NULL AND checklist_humor.notas != '' AND EXCLUDED.notas IS NOT NULL THEN checklist_humor.notas || E'\n' || EXCLUDED.notas
                ELSE COALESCE(EXCLUDED.notas, checklist_humor.notas)
            END
        """, (checklist_id, h.get('humor_geral'), h.get('teve_crise'), h.get('o_que_acalmou'), h.get('notas')))

    # ROTINA
    if "rotina" in campos and campos["rotina"]:
        r = campos["rotina"]
        cur.execute("""
            INSERT INTO checklist_rotina (checklist_id, guardou_brinquedos, ajudou_tarefa, aceitou_transicao)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (checklist_id) DO UPDATE SET 
            guardou_brinquedos = COALESCE(EXCLUDED.guardou_brinquedos, checklist_rotina.guardou_brinquedos),
            ajudou_tarefa = COALESCE(EXCLUDED.ajudou_tarefa, checklist_rotina.ajudou_tarefa),
            aceitou_transicao = COALESCE(EXCLUDED.aceitou_transicao, checklist_rotina.aceitou_transicao)
        """, (checklist_id, r.get('guardou_brinquedos'), r.get('ajudou_tarefa'), r.get('aceitou_transicao')))


def buscar_campos_ausentes(crianca_id: str, data_ref: str = None) -> list[str]:
    """
    Consulta o banco para verificar quais tabelas filhas do checklist estão vazias.
    Retorna uma lista ordenada por prioridade (PROMPT B4) dos campos ausentes.
    
    Se data_ref não for fornecida, consulta a data de hoje.
    """
    if not data_ref:
        data_ref = date.today().isoformat()

    campos_ausentes = []

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Primeiro, verificar se existe checklist para o dia
                cur.execute("""
                    SELECT id FROM checklists 
                    WHERE crianca_id = %s AND data = %s
                """, (crianca_id, data_ref))
                checklist_row = cur.fetchone()

                if not checklist_row:
                    # Nenhum checklist para o dia — todos os campos estão ausentes
                    return list(PRIORIDADE_CAMPOS)

                checklist_id = checklist_row['id']

                # Verificar cada tabela filha
                for campo in PRIORIDADE_CAMPOS:
                    config = CAMPO_CONFIG.get(campo)
                    if not config:
                        continue
                    tabela = config["tabela"]
                    cur.execute(f"SELECT 1 FROM {tabela} WHERE checklist_id = %s", (checklist_id,))
                    if not cur.fetchone():
                        campos_ausentes.append(campo)

    except Exception as e:
        logger.error(f"Erro ao buscar campos ausentes: {e}")
        return list(PRIORIDADE_CAMPOS)  # Em caso de erro, assume todos ausentes

    return campos_ausentes


def obter_checklist_id_do_dia(crianca_id: str, data_ref: str = None) -> str | None:
    """Retorna o checklist_id do dia, se existir."""
    if not data_ref:
        data_ref = date.today().isoformat()
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id FROM checklists
                    WHERE crianca_id = %s AND data = %s
                """, (crianca_id, data_ref))
                row = cur.fetchone()
                return str(row['id']) if row else None
    except Exception as e:
        logger.error(f"Erro ao obter checklist_id do dia: {e}")
        return None