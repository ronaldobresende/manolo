"""Estruturação e preenchimento do checklist diário.

Responsável por salvar dados parciais de rotina e consultar campos ausentes para cobrança conversacional.
"""

import logging
import json
from datetime import date, timedelta
from typing import Optional, List
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
    
    # SONO
    if "sono" in campos and campos["sono"]:
        o = campos.get('sono')
        if o is not None:
            cur.execute("""
                INSERT INTO checklist_sono (checklist_id, dormiu_as, acordou_as, acordou_noite, cochilo_inicio, cochilo_fim, notas)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (checklist_id) DO UPDATE SET 
                    dormiu_as = COALESCE(EXCLUDED.dormiu_as, checklist_sono.dormiu_as),
                    acordou_as = COALESCE(EXCLUDED.acordou_as, checklist_sono.acordou_as),
                    acordou_noite = COALESCE(EXCLUDED.acordou_noite, checklist_sono.acordou_noite),
                    cochilo_inicio = COALESCE(EXCLUDED.cochilo_inicio, checklist_sono.cochilo_inicio),
                    cochilo_fim = COALESCE(EXCLUDED.cochilo_fim, checklist_sono.cochilo_fim),
                    notas = COALESCE(EXCLUDED.notas, checklist_sono.notas)
            """, (checklist_id, o.get('dormiu_as'), o.get('acordou_as'), o.get('acordou_noite'), o.get('cochilo_inicio'), o.get('cochilo_fim'), o.get('notas')))

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
                aceitou = array_cat(COALESCE(checklist_alimentacao.aceitou, ARRAY[]::TEXT[]), COALESCE(EXCLUDED.aceitou, ARRAY[]::TEXT[])),
                recusou = array_cat(COALESCE(checklist_alimentacao.recusou, ARRAY[]::TEXT[]), COALESCE(EXCLUDED.recusou, ARRAY[]::TEXT[])),
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
                palavras_ditas = array_cat(COALESCE(checklist_comunicacao.palavras_ditas, ARRAY[]::TEXT[]), COALESCE(EXCLUDED.palavras_ditas, ARRAY[]::TEXT[])),
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
                com_que_brincou = array_cat(COALESCE(checklist_brincar.com_que_brincou, ARRAY[]::TEXT[]), COALESCE(EXCLUDED.com_que_brincou, ARRAY[]::TEXT[])),
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
                atividades = array_cat(COALESCE(checklist_movimento.atividades, ARRAY[]::TEXT[]), COALESCE(EXCLUDED.atividades, ARRAY[]::TEXT[])),
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
                notas = COALESCE(EXCLUDED.notas, checklist_humor.notas)
        """, (checklist_id, h.get('humor_geral'), h.get('teve_crise'), h.get('o_que_acalmou'), h.get('notas')))

    # ROTINA
    if "rotina" in campos and campos["rotina"]:
        r = campos["rotina"]
        cur.execute("""
            INSERT INTO checklist_rotina (checklist_id, guardou_brinquedos, ajudou_tarefa, aceitou_transicao, teve_escola)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (checklist_id) DO UPDATE SET
                guardou_brinquedos = COALESCE(EXCLUDED.guardou_brinquedos, checklist_rotina.guardou_brinquedos),
                ajudou_tarefa = COALESCE(EXCLUDED.ajudou_tarefa, checklist_rotina.ajudou_tarefa),
                aceitou_transicao = COALESCE(EXCLUDED.aceitou_transicao, checklist_rotina.aceitou_transicao),
                teve_escola = COALESCE(EXCLUDED.teve_escola, checklist_rotina.teve_escola)
        """, (checklist_id, r.get('guardou_brinquedos'), r.get('ajudou_tarefa'), r.get('aceitou_transicao'), r.get('teve_escola')))

    # OBSERVACOES
    if "observacoes" in campos and campos["observacoes"]:
        o = campos["observacoes"]
        cur.execute("""
            INSERT INTO checklist_observacoes (checklist_id, conquistas, dificuldades, diferente_hoje)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (checklist_id) DO UPDATE SET
                conquistas = NULLIF(CONCAT_WS('\n', NULLIF(checklist_observacoes.conquistas, ''), NULLIF(EXCLUDED.conquistas, '')), ''),
                dificuldades = NULLIF(CONCAT_WS('\n', NULLIF(checklist_observacoes.dificuldades, ''), NULLIF(EXCLUDED.dificuldades, '')), ''),
                diferente_hoje = NULLIF(CONCAT_WS('\n', NULLIF(checklist_observacoes.diferente_hoje, ''), NULLIF(EXCLUDED.diferente_hoje, '')), '')
        """, (checklist_id, o.get('conquistas'), o.get('dificuldades'), o.get('diferente_hoje')))

    # TERAPIAS
    if "sessoes_terapia" in campos and campos["sessoes_terapia"]:
        # Busca os metadados do dia a partir do checklist_id
        cur.execute("SELECT crianca_id, usuario_id, data FROM checklists WHERE id = %s", (checklist_id,))
        row_chk = cur.fetchone()
        if row_chk:
            for t in campos["sessoes_terapia"]:
                cur.execute("""
                    INSERT INTO sessoes_terapia (crianca_id, usuario_id, data, horario_inicio, horario_fim, especialidade, notas)
                    VALUES (%s, %s, %s, %s, %s, COALESCE(%s, 'Geral'), %s)
                    ON CONFLICT (crianca_id, data, especialidade) DO UPDATE SET
                        horario_inicio = COALESCE(sessoes_terapia.horario_inicio, EXCLUDED.horario_inicio),
                        horario_fim = COALESCE(EXCLUDED.horario_fim, sessoes_terapia.horario_fim),
                        notas = NULLIF(CONCAT_WS('\n', NULLIF(sessoes_terapia.notas, ''), NULLIF(EXCLUDED.notas, '')), '')
                """, (row_chk['crianca_id'], row_chk['usuario_id'], row_chk['data'], t.get('horario_inicio'), t.get('horario_fim'), t.get('especialidade'), t.get('notas_sessao')))


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


def mesclar_checklists(crianca_id: str, data_origem: str, data_destino: str) -> bool:
    """
    Move todos os registros das tabelas filhas do checklist da data_origem para a data_destino.
    Resolve conflitos priorizando ou mesclando os dados com a data_destino.
    """
    if data_origem == data_destino:
        return True

    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Obter os IDs
                cur.execute("SELECT id FROM checklists WHERE crianca_id = %s AND data = %s", (crianca_id, data_origem))
                row_origem = cur.fetchone()
                if not row_origem:
                    return True  # Nada a mesclar

                id_origem = row_origem['id']

                cur.execute("SELECT id FROM checklists WHERE crianca_id = %s AND data = %s", (crianca_id, data_destino))
                row_destino = cur.fetchone()

                # Se não existir destino, simplesmente atualizamos a data do checklist origem
                if not row_destino:
                    cur.execute("UPDATE checklists SET data = %s WHERE id = %s", (data_destino, id_origem))
                    conn.commit()
                    logger.info(f"[MESCLA] Checklist {id_origem} movido de {data_origem} para {data_destino}.")
                    return True

                id_destino = row_destino['id']

                # Se ambos existem, precisamos transferir tabela a tabela
                tabelas = [
                    'checklist_sono', 'checklist_alimentacao', 'checklist_brincar', 
                    'checklist_comunicacao', 'checklist_higiene', 'checklist_humor', 
                    'checklist_movimento', 'checklist_rotina', 'checklist_tela', 
                    'checklist_vestuario'
                ]

                for tabela in tabelas:
                    cur.execute(f"SELECT * FROM {tabela} WHERE checklist_id = %s", (id_origem,))
                    dados_origem = cur.fetchone()
                    
                    if dados_origem:
                        cur.execute(f"SELECT * FROM {tabela} WHERE checklist_id = %s", (id_destino,))
                        dados_destino = cur.fetchone()
                        
                        if not dados_destino:
                            # Destino não tem essa tabela, só atualizar o ID
                            cur.execute(f"UPDATE {tabela} SET checklist_id = %s WHERE checklist_id = %s", (id_destino, id_origem))
                        else:
                            # Destino já tem. Num cenário MVP, vamos atualizar os dados do destino com coalescência 
                            # (isso exigiria lógica dinâmica complexa em SQL ou Python).
                            # Por simplicidade do MVP, vamos dar preferência à origem (já que é o relato mais recente que a mãe corrigiu).
                            
                            # Remove ID original do dict
                            colunas = [k for k in dados_origem.keys() if k not in ('id', 'checklist_id', 'criado_em', 'atualizado_em')]
                            set_clause = ", ".join([f"{col} = COALESCE(%s, {tabela}.{col})" for col in colunas])
                            valores = [dados_origem[col] for col in colunas]
                            valores.append(id_destino)
                            
                            cur.execute(f"UPDATE {tabela} SET {set_clause} WHERE checklist_id = %s", tuple(valores))
                            cur.execute(f"DELETE FROM {tabela} WHERE checklist_id = %s", (id_origem,))
                            
                # Exclui o checklist origem (as tabelas filhas já foram movidas/deletadas)
                cur.execute("DELETE FROM checklists WHERE id = %s", (id_origem,))
                conn.commit()
                logger.info(f"[MESCLA] Checklist {id_origem} ({data_origem}) mesclado em {id_destino} ({data_destino}).")
                return True
                
    except Exception as e:
        logger.error(f"Erro ao mesclar checklists de {data_origem} para {data_destino}: {e}")
        return False



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


def formatar_resumo_diario(crianca_id: str, data_ref: str) -> str:
    """Busca o checklist da data no banco e gera a string formatada com emojis."""
    from psycopg2.extras import RealDictCursor
    from datetime import datetime
    
    try:
        data_fmt = datetime.strptime(data_ref, "%Y-%m-%d").strftime("%d/%m/%Y")
    except:
        data_fmt = data_ref

    resumo = f"📋 Checklist — {data_fmt}\n\n"
    
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id FROM checklists WHERE crianca_id = %s AND data = %s", (crianca_id, data_ref))
                row = cur.fetchone()
                
                if not row:
                    return resumo + "Ainda não há nenhum registro para este dia. Pode me contar como foi!\n\nComplete no app: https://app.manolo.com"
                
                checklist_id = row['id']

                def format_time(t):
                    if not t: return '?'
                    if hasattr(t, 'strftime'): return t.strftime('%H:%M')
                    return str(t)[:5]
                
                def format_list(l):
                    if not l: return ''
                    if isinstance(l, list): return ', '.join(l)
                    return str(l)
                    
                def format_duration(m):
                    if not m: return '0m'
                    h = m // 60
                    mins = m % 60
                    if h == 0: return f"{mins}m"
                    return f"{h}h{str(mins).zfill(2)}m"

                def format_bool(val, str_true, str_false):
                    if val is True: return str_true
                    if val is False: return str_false
                    return "não informado"

                # Funções de formatação mais detalhadas e rigorosas com booleanos
                def formata_alimentacao(r):
                    partes = []
                    partes.append(format_bool(r.get('comeu_bem'), "comeu bem", "não comeu tão bem"))
                    partes.append(format_bool(r.get('comeu_sentado'), "comeu sentado", "não comeu sentado"))
                    if r.get('aceitou'): partes.append(f"aceitou: {format_list(r.get('aceitou'))}")
                    if r.get('recusou'): partes.append(f"recusou: {format_list(r.get('recusou'))}")
                    if r.get('utensilio'): partes.append(f"usou {r.get('utensilio')}")
                    return " | ".join(p for p in partes if p and p != "não informado")

                def formata_comunicacao(r):
                    partes = []
                    if r.get('palavras_ditas'): partes.append(f"falou: {format_list(r.get('palavras_ditas'))}")
                    if r.get('usou_gestos') is True: partes.append("usou gestos")
                    if r.get('apontou') is True: partes.append("apontou")
                    if r.get('imitou') is True: partes.append("imitou")
                    if r.get('respondeu_nome'): partes.append(f"respondeu ao nome: {r.get('respondeu_nome')}")
                    if r.get('puxou_mao'): partes.append(f"puxou a mão: {r.get('puxou_mao')}")
                    return " | ".join(partes) if partes else "sem detalhes"

                def formata_brincar(r):
                    partes = []
                    if r.get('com_que_brincou'): partes.append(f"brincou de: {format_list(r.get('com_que_brincou'))}")
                    if r.get('modo'): partes.append(f"modo: {r.get('modo')}")
                    if r.get('fez_faz_de_conta') is True: partes.append("fez faz de conta")
                    if r.get('tempo_sem_tela_minutos'): partes.append(f"tempo brincando: {format_duration(r.get('tempo_sem_tela_minutos'))}")
                    return " | ".join(partes) if partes else "sem detalhes"

                def formata_higiene(r):
                    partes = [f"banho foi {r.get('banho') or 'ok'}"]
                    if r.get('escovou_dentes') is True: partes.append("escovou dentes")
                    if r.get('sinalizou_banheiro') is True: partes.append("sinalizou banheiro")
                    return " | ".join(partes)

                def formata_vestuario(r):
                    partes = []
                    partes.append(format_bool(r.get('colaborou_roupa'), "colaborou com a roupa", "não colaborou com a roupa"))
                    partes.append(format_bool(r.get('incomodo_sensorial'), "teve incômodo sensorial", "sem incômodo sensorial"))
                    return " | ".join(p for p in partes if p and p != "não informado") or "sem detalhes"

                def formata_movimento(r):
                    partes = []
                    if r.get('atividades'): partes.append(format_list(r.get('atividades')))
                    if r.get('caiu_muito') is True: partes.append("caiu muito")
                    if r.get('buscou_colo') is True: partes.append("buscou bastante colo")
                    return " | ".join(partes) if partes else "sem detalhes"

                def formata_rotina(r):
                    partes = []
                    if r.get('teve_escola') is not None:
                        partes.append(f"escola: {'sim' if r.get('teve_escola') else 'não'}")
                    if r.get('aceitou_transicao') is not None:
                        partes.append("aceitou transições" if r.get('aceitou_transicao') else "resistiu a transições")
                    if r.get('guardou_brinquedos') is not None:
                        partes.append("guardou brinquedos" if r.get('guardou_brinquedos') else "não guardou brinquedos")
                    if r.get('ajudou_tarefa') is not None:
                        partes.append("ajudou nas tarefas" if r.get('ajudou_tarefa') else "não ajudou nas tarefas")
                    return " | ".join(partes) if partes else "sem detalhes"

                def formata_sono(r):
                    base = f"dormiu às {format_time(r.get('dormiu_as'))}, acordou às {format_time(r.get('acordou_as'))}"
                    if r.get('acordou_noite') is True:
                        base += " | acordou na noite"
                    if r.get('cochilo_inicio') or r.get('cochilo_fim'):
                        base += f" | cochilou ({format_time(r.get('cochilo_inicio'))} - {format_time(r.get('cochilo_fim'))})"
                    return base

                # Campos na ordem pedida
                campos = [
                    ("sono", "checklist_sono", "Sono", formata_sono),
                    ("alimentacao", "checklist_alimentacao", "Alimentação", formata_alimentacao),
                    ("tela", "checklist_tela", "Tela", lambda r: f"usou por {format_duration(r.get('tempo_minutos'))}{(' (' + r.get('conteudo') + ')') if r.get('conteudo') else ''}" if r.get('usou_tela') is True else ("não usou telas hoje! 🎉" if r.get('usou_tela') is False else "não informado")),
                    ("comunicacao", "checklist_comunicacao", "Comunicação", formata_comunicacao),
                    ("brincar", "checklist_brincar", "Brincar", formata_brincar),
                    ("humor", "checklist_humor", "Humor", lambda r: f"{r.get('humor_geral') or 'bom'}{' | teve crise' if r.get('teve_crise') is True else ''}{(' | acalmou com: ' + r.get('o_que_acalmou')) if r.get('o_que_acalmou') else ''}"),
                    ("higiene", "checklist_higiene", "Higiene", formata_higiene),
                    ("vestuario", "checklist_vestuario", "Vestuário", formata_vestuario),
                    ("movimento", "checklist_movimento", "Movimento", formata_movimento),
                    ("rotina", "checklist_rotina", "Rotina", formata_rotina),
                ]
                
                for key, tabela, nome, formatador in campos:
                    cur.execute(f"SELECT * FROM {tabela} WHERE checklist_id = %s", (checklist_id,))
                    dados = cur.fetchone()
                    if dados:
                        desc = formatador(dados)
                        resumo += f"✅ {nome}: {desc}\n"
                    else:
                        resumo += f"⬜ {nome}: não registrado\n"
                        
                # Adiciona seção de terapias
                cur.execute("SELECT * FROM sessoes_terapia WHERE crianca_id = %s AND data = %s ORDER BY horario_inicio", (crianca_id, data_ref))
                terapias = cur.fetchall()
                if terapias:
                    resumo += "\n🏥 Sessões de Terapia:\n"
                    for t in terapias:
                        horario = ""
                        if t.get('horario_inicio') or t.get('horario_fim'):
                            horario = f"({format_time(t.get('horario_inicio'))} - {format_time(t.get('horario_fim'))}) "
                        resumo += f"- {horario}{t.get('especialidade')}: {t.get('notas') or 'sem notas'}\n"
                        
    except Exception as e:
        logger.error(f"Erro ao formatar resumo: {e}")
        return f"Não consegui buscar o relatório de {data_fmt}."
        
    resumo += "\nComplete o que faltou no app: https://www.manolo.app.br/dashboard/checklists"
    return resumo