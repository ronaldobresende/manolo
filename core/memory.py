"""Leitura e escrita no banco de dados e histórico."""

import os
import logging
from openai import OpenAI
from core.database import get_connection

logger = logging.getLogger(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def buscar_contexto_documentos(pergunta: str, crianca_id: str, limite: int = 5) -> str:
    """Busca os chunks de documentos mais relevantes para a pergunta (Busca Semântica RAG)."""
    try:
        # 1. Transforma a pergunta do usuário em um vetor
        response = client.embeddings.create(input=pergunta, model="text-embedding-3-small")
        embedding_pergunta = response.data[0].embedding
        emb_str = f"[{','.join(map(str, embedding_pergunta))}]"
        
        # 2. Busca no banco pela distância de cosseno (<=>) usando o pgvector
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT conteudo, 
                           1 - (embedding <=> %s::vector) as similaridade
                    FROM documento_chunks
                    WHERE crianca_id = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (emb_str, crianca_id, emb_str, limite))
                
                resultados = cur.fetchall()
        
        if not resultados:
            return "Nenhum documento histórico relevante encontrado para essa pergunta."
            
        contexto = ""
        for i, row in enumerate(resultados):
            contexto += f"--- Trecho Documento {i+1} ---\n{row['conteudo']}\n\n"
        return contexto
        
    except Exception as e:
        logger.error(f"Erro na busca vetorial: {e}")
        return ""

def obter_perfil_vivo(crianca_id: str) -> str:
    """Recupera o perfil vivo atual da criança direto do banco."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM perfil_crianca WHERE crianca_id = %s", (crianca_id,))
                perfil = cur.fetchone()
                if perfil:
                    # Retorna os dados agregados para colocar no Prompt
                    return f"Comunicação: {perfil['comunicacao']}\nMotor: {perfil['motor']}\nAlimentação: {perfil['alimentacao']}\nSono: {perfil['sono']}\nRegulação: {perfil['regulacao']}\nResumo Geral: {perfil['resumo_geral']}"
    except Exception as e:
        logger.error(f"Erro ao buscar perfil vivo: {e}")
    return "Perfil não encontrado ou não inicializado."

def buscar_contexto_checklists(crianca_id: str, limite_dias: int = 7) -> str:
    """
    Busca os últimos checklists diários no banco relacional, fazendo JOIN com
    todas as tabelas filhas para fornecer contexto completo ao RAG.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        c.id as checklist_id,
                        c.data,
                        -- Sono
                        cs.dormiu_as, cs.acordou_as, cs.acordou_noite, cs.cochilo_inicio, cs.cochilo_fim, cs.notas as sono_notas,
                        -- Humor
                        ch.humor_geral, ch.teve_crise, ch.o_que_acalmou, ch.notas as humor_notas,
                        -- Alimentação
                        ca.comeu_bem, ca.aceitou, ca.recusou, ca.comeu_sentado, ca.utensilio,
                        -- Comunicação
                        cc.usou_gestos, cc.palavras_ditas, cc.apontou, cc.respondeu_nome, cc.imitou,
                        -- Brincar
                        cb.com_que_brincou, cb.modo as brincar_modo, cb.fez_faz_de_conta,
                        -- Higiene
                        chi.banho, chi.escovou_dentes, chi.sinalizou_banheiro,
                        -- Vestuário
                        cv.colaborou_roupa, cv.incomodo_sensorial,
                        -- Movimento
                        cm.atividades as mov_atividades, cm.caiu_muito, cm.buscou_colo,
                        -- Tela
                        ct.usou_tela, ct.tempo_minutos as tela_minutos, ct.conteudo as tela_conteudo, ct.reacao_retirada,
                        -- Rotina
                        cr.guardou_brinquedos, cr.ajudou_tarefa, cr.aceitou_transicao,
                        -- Observações
                        co.conquistas, co.dificuldades, co.diferente_hoje
                    FROM checklists c
                    LEFT JOIN checklist_sono cs ON c.id = cs.checklist_id
                    LEFT JOIN checklist_humor ch ON c.id = ch.checklist_id
                    LEFT JOIN checklist_alimentacao ca ON c.id = ca.checklist_id
                    LEFT JOIN checklist_comunicacao cc ON c.id = cc.checklist_id
                    LEFT JOIN checklist_brincar cb ON c.id = cb.checklist_id
                    LEFT JOIN checklist_higiene chi ON c.id = chi.checklist_id
                    LEFT JOIN checklist_vestuario cv ON c.id = cv.checklist_id
                    LEFT JOIN checklist_movimento cm ON c.id = cm.checklist_id
                    LEFT JOIN checklist_tela ct ON c.id = ct.checklist_id
                    LEFT JOIN checklist_rotina cr ON c.id = cr.checklist_id
                    LEFT JOIN checklist_observacoes co ON c.id = co.checklist_id
                    WHERE c.crianca_id = %s
                    ORDER BY c.data DESC
                    LIMIT %s
                """, (crianca_id, limite_dias))
                resultados = cur.fetchall()

        if not resultados:
            return "Nenhum checklist recente encontrado."

        contexto = ""
        for row in resultados:
            contexto += f"--- Registro do dia {row['data']} ---\n"

            # Sono
            partes_sono = []
            if row.get('dormiu_as'): partes_sono.append(f"dormiu às {row['dormiu_as']}")
            if row.get('acordou_as'): partes_sono.append(f"acordou às {row['acordou_as']}")
            if row.get('cochilo_inicio') or row.get('cochilo_fim'): 
                partes_sono.append(f"cochilou das {row.get('cochilo_inicio') or '?'} às {row.get('cochilo_fim') or '?'}")
            if row.get('acordou_noite') is True: partes_sono.append("acordou à noite")
            if row.get('sono_notas'): partes_sono.append(row['sono_notas'])
            if partes_sono:
                contexto += f"Sono: {', '.join(partes_sono)}.\n"

            # Humor
            partes_humor = []
            if row.get('humor_geral'): partes_humor.append(f"humor {row['humor_geral']}")
            if row.get('teve_crise') is True: partes_humor.append("teve crise")
            if row.get('o_que_acalmou'): partes_humor.append(f"acalmou com {row['o_que_acalmou']}")
            if row.get('humor_notas'): partes_humor.append(row['humor_notas'])
            if partes_humor:
                contexto += f"Humor/Regulação: {', '.join(partes_humor)}.\n"

            # Alimentação
            partes_alim = []
            if row.get('comeu_bem') is True: partes_alim.append("comeu bem")
            elif row.get('comeu_bem') is False: partes_alim.append("não comeu bem")
            if row.get('aceitou'): partes_alim.append(f"aceitou: {', '.join(row['aceitou'])}")
            if row.get('recusou'): partes_alim.append(f"recusou: {', '.join(row['recusou'])}")
            if row.get('comeu_sentado') is True: partes_alim.append("comeu sentado")
            if row.get('utensilio'): partes_alim.append(f"usou {row['utensilio']}")
            if partes_alim:
                contexto += f"Alimentação: {', '.join(partes_alim)}.\n"

            # Comunicação
            partes_com = []
            if row.get('palavras_ditas'): partes_com.append(f"palavras: {', '.join(row['palavras_ditas'])}")
            if row.get('usou_gestos') is True: partes_com.append("usou gestos")
            if row.get('apontou') is True: partes_com.append("apontou")
            if row.get('respondeu_nome'): partes_com.append(f"respondeu ao nome: {row['respondeu_nome']}")
            if row.get('imitou') is True: partes_com.append("imitou")
            if partes_com:
                contexto += f"Comunicação: {', '.join(partes_com)}.\n"

            # Brincar
            partes_brincar = []
            if row.get('com_que_brincou'): partes_brincar.append(f"brincou com: {', '.join(row['com_que_brincou'])}")
            if row.get('brincar_modo'): partes_brincar.append(f"modo: {row['brincar_modo']}")
            if row.get('fez_faz_de_conta') is True: partes_brincar.append("fez faz-de-conta")
            if partes_brincar:
                contexto += f"Brincar: {', '.join(partes_brincar)}.\n"

            # Tela
            partes_tela = []
            if row.get('usou_tela') is True:
                partes_tela.append("usou tela")
                if row.get('tela_minutos'): partes_tela.append(f"por {row['tela_minutos']} minutos")
                if row.get('tela_conteudo'): partes_tela.append(f"conteúdo: {row['tela_conteudo']}")
                if row.get('reacao_retirada'): partes_tela.append(f"reação ao tirar: {row['reacao_retirada']}")
            elif row.get('usou_tela') is False:
                partes_tela.append("não usou tela")
            if partes_tela:
                contexto += f"Tela: {', '.join(partes_tela)}.\n"

            # Higiene
            partes_hig = []
            if row.get('banho'): partes_hig.append(f"banho: {row['banho']}")
            if row.get('escovou_dentes') is True: partes_hig.append("escovou os dentes")
            if row.get('sinalizou_banheiro') is True: partes_hig.append("sinalizou banheiro")
            if partes_hig:
                contexto += f"Higiene: {', '.join(partes_hig)}.\n"

            # Movimento
            partes_mov = []
            if row.get('mov_atividades'): partes_mov.append(f"atividades: {', '.join(row['mov_atividades'])}")
            if row.get('buscou_colo') is True: partes_mov.append("buscou colo")
            if row.get('caiu_muito') is True: partes_mov.append("caiu muito")
            if partes_mov:
                contexto += f"Movimento: {', '.join(partes_mov)}.\n"

            # Vestuário
            partes_vest = []
            if row.get('colaborou_roupa') is True: partes_vest.append("colaborou com a roupa")
            elif row.get('colaborou_roupa') is False: partes_vest.append("não colaborou com a roupa")
            if row.get('incomodo_sensorial') is True: partes_vest.append("teve incômodo sensorial")
            if partes_vest:
                contexto += f"Vestuário: {', '.join(partes_vest)}.\n"

            # Rotina
            partes_rot = []
            if row.get('guardou_brinquedos') is True: partes_rot.append("guardou brinquedos")
            if row.get('ajudou_tarefa') is True: partes_rot.append("ajudou em tarefa")
            if row.get('aceitou_transicao') is True: partes_rot.append("aceitou transição bem")
            elif row.get('aceitou_transicao') is False: partes_rot.append("dificuldade na transição de atividades")
            if partes_rot:
                contexto += f"Rotina: {', '.join(partes_rot)}.\n"

            # Observações livres
            if row.get('conquistas'): contexto += f"Conquistas: {row['conquistas']}.\n"
            if row.get('dificuldades'): contexto += f"Dificuldades: {row['dificuldades']}.\n"
            if row.get('diferente_hoje'): contexto += f"Algo diferente: {row['diferente_hoje']}.\n"

            contexto += "\n"

        return contexto

    except Exception as e:
        logger.error(f"Erro ao buscar checklists: {e}")
        return ""