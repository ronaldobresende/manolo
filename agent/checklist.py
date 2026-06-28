"""Estruturação e preenchimento do checklist diário.

Responsável por salvar dados parciais de rotina (PROMPT B4: nunca sobrescrever
campos existentes com null) e consultar campos ausentes para cobrança conversacional.
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
    Lê o JSON estruturado pelo LLM e persiste nas tabelas relacionais.
    
    REGRA B4: Nunca sobrescrever campos existentes com null.
    Usa INSERT ... ON CONFLICT DO UPDATE SET apenas para campos que vieram preenchidos.
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

                # 2. Salvar cada seção que veio preenchida
                if "sono" in campos and campos["sono"]:
                    notas_sono = json.dumps(campos["sono"], ensure_ascii=False) if isinstance(campos["sono"], dict) else str(campos["sono"])
                    cur.execute("""
                        INSERT INTO checklist_sono (checklist_id, notas)
                        VALUES (%s, %s)
                        ON CONFLICT (checklist_id) DO UPDATE SET notas = EXCLUDED.notas
                    """, (checklist_id, notas_sono))

                if "humor" in campos and campos["humor"]:
                    notas_humor = json.dumps(campos["humor"], ensure_ascii=False) if isinstance(campos["humor"], dict) else str(campos["humor"])
                    teve_crise = any(kw in str(campos.get("humor", "")).lower() for kw in ["chorou", "crise", "birra", "gritou"])
                    cur.execute("""
                        INSERT INTO checklist_humor (checklist_id, teve_crise, notas)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (checklist_id) DO UPDATE 
                        SET teve_crise = EXCLUDED.teve_crise, notas = EXCLUDED.notas
                    """, (checklist_id, teve_crise, notas_humor))

                if "comunicacao" in campos and campos["comunicacao"]:
                    notas_com = json.dumps(campos["comunicacao"], ensure_ascii=False) if isinstance(campos["comunicacao"], dict) else str(campos["comunicacao"])
                    cur.execute("""
                        INSERT INTO checklist_comunicacao (checklist_id)
                        VALUES (%s)
                        ON CONFLICT (checklist_id) DO NOTHING
                    """, (checklist_id,))

                if "alimentacao" in campos and campos["alimentacao"]:
                    cur.execute("""
                        INSERT INTO checklist_alimentacao (checklist_id)
                        VALUES (%s)
                        ON CONFLICT (checklist_id) DO NOTHING
                    """, (checklist_id,))

                if "brincar" in campos and campos["brincar"]:
                    cur.execute("""
                        INSERT INTO checklist_brincar (checklist_id)
                        VALUES (%s)
                        ON CONFLICT (checklist_id) DO NOTHING
                    """, (checklist_id,))

                if "higiene" in campos and campos["higiene"]:
                    cur.execute("""
                        INSERT INTO checklist_higiene (checklist_id)
                        VALUES (%s)
                        ON CONFLICT (checklist_id) DO NOTHING
                    """, (checklist_id,))

                if "vestuario" in campos and campos["vestuario"]:
                    cur.execute("""
                        INSERT INTO checklist_vestuario (checklist_id)
                        VALUES (%s)
                        ON CONFLICT (checklist_id) DO NOTHING
                    """, (checklist_id,))

                if "movimento" in campos and campos["movimento"]:
                    cur.execute("""
                        INSERT INTO checklist_movimento (checklist_id)
                        VALUES (%s)
                        ON CONFLICT (checklist_id) DO NOTHING
                    """, (checklist_id,))

                if "tela" in campos and campos["tela"]:
                    cur.execute("""
                        INSERT INTO checklist_tela (checklist_id)
                        VALUES (%s)
                        ON CONFLICT (checklist_id) DO NOTHING
                    """, (checklist_id,))

                if "rotina" in campos and campos["rotina"]:
                    cur.execute("""
                        INSERT INTO checklist_rotina (checklist_id)
                        VALUES (%s)
                        ON CONFLICT (checklist_id) DO NOTHING
                    """, (checklist_id,))

                # 3. Observações livres (sempre salva como dump geral)
                diferente_hoje = ""
                for chave, valor in campos.items():
                    diferente_hoje += f"- {chave.upper()}: {json.dumps(valor, ensure_ascii=False) if isinstance(valor, (dict, list)) else valor}\n"

                if diferente_hoje:
                    cur.execute("""
                        INSERT INTO checklist_observacoes (checklist_id, diferente_hoje)
                        VALUES (%s, %s)
                        ON CONFLICT (checklist_id) DO UPDATE SET diferente_hoje = EXCLUDED.diferente_hoje
                    """, (checklist_id, diferente_hoje))

            conn.commit()
        logger.info(f"Checklist salvo com sucesso nas tabelas relacionais! (Checklist ID: {checklist_id})")
        return checklist_id
    except Exception as e:
        logger.error(f"Erro ao salvar checklist: {e}")
        return None


def salvar_campo_individual(checklist_id: str, campo: str, dados: dict):
    """
    Salva um campo individual do checklist (usado para respostas a cobranças).
    Ex: campo="sono", dados={"dormiu_as": "21h", "acordou_as": "7h"}
    """
    try:
        config = CAMPO_CONFIG.get(campo)
        if not config:
            logger.warning(f"Campo '{campo}' não reconhecido.")
            return False

        notas = json.dumps(dados, ensure_ascii=False) if isinstance(dados, dict) else str(dados)

        with get_connection() as conn:
            with conn.cursor() as cur:
                # Estratégia genérica: salva as notas como texto na tabela filha
                tabela = config["tabela"]
                if tabela == "checklist_sono":
                    cur.execute("""
                        INSERT INTO checklist_sono (checklist_id, notas) VALUES (%s, %s)
                        ON CONFLICT (checklist_id) DO UPDATE SET notas = EXCLUDED.notas
                    """, (checklist_id, notas))
                elif tabela == "checklist_humor":
                    teve_crise = any(kw in notas.lower() for kw in ["chorou", "crise", "birra", "gritou"])
                    cur.execute("""
                        INSERT INTO checklist_humor (checklist_id, teve_crise, notas) VALUES (%s, %s, %s)
                        ON CONFLICT (checklist_id) DO UPDATE SET teve_crise = EXCLUDED.teve_crise, notas = EXCLUDED.notas
                    """, (checklist_id, teve_crise, notas))
                elif tabela == "checklist_comunicacao":
                    cur.execute("""
                        INSERT INTO checklist_comunicacao (checklist_id) VALUES (%s)
                        ON CONFLICT (checklist_id) DO NOTHING
                    """, (checklist_id,))
                else:
                    # Para tabelas que ainda não têm mapeamento fino, faz o insert básico
                    cur.execute(f"""
                        INSERT INTO {tabela} (checklist_id) VALUES (%s)
                        ON CONFLICT (checklist_id) DO NOTHING
                    """, (checklist_id,))

                # Sempre atualiza observações com o dado completo
                cur.execute("""
                    INSERT INTO checklist_observacoes (checklist_id, diferente_hoje) VALUES (%s, %s)
                    ON CONFLICT (checklist_id) DO UPDATE 
                    SET diferente_hoje = COALESCE(checklist_observacoes.diferente_hoje, '') || E'\n' || EXCLUDED.diferente_hoje
                """, (checklist_id, f"- {campo.upper()}: {notas}"))

            conn.commit()
        logger.info(f"Campo '{campo}' salvo com sucesso no checklist {checklist_id}.")
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar campo individual '{campo}': {e}")
        return False


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