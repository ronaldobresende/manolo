"""Orquestração do agente via LangGraph.

Motor central do Manolo: recebe mensagens (texto ou transcrição de áudio),
extrai silenciosamente dados de checklist, classifica a intenção, roteia
para RAG ou checklist, e cobra campos ausentes de forma conversacional.
"""

import logging
import json
from datetime import datetime, date
from typing import TypedDict, Literal

import pytz
from langsmith import traceable
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from core.memory import buscar_contexto_documentos, obter_perfil_vivo, buscar_contexto_checklists
from core.clients import get_openai_client
from core.config import settings
from core.schemas import (
    LLMChecklistResponse, SonoModel, HumorModel, ComunicacaoModel,
    AlimentacaoModel, BrincarModel, HigieneModel, MovimentoModel,
    VestuarioModel, TelaModel, RotinaModel
)
from agent.checklist import (
    salvar_checklist,
    buscar_campos_ausentes,
    obter_checklist_id_do_dia,
    _obter_ou_criar_checklist,
    mesclar_checklists,
    formatar_resumo_diario
)
from agent.profile import atualizar_perfil

logger = logging.getLogger(__name__)


# ============================================================
# 1. DEFINIÇÃO DO ESTADO
# ============================================================

class ManoloState(TypedDict):
    # Entrada (imutáveis por mensagem)
    mensagem: str
    telefone: str
    usuario_id: str
    nome_usuario: str
    perfil_usuario: str
    crianca_id: str

    # Controle de fluxo (gerenciados pelo grafo)
    intencao: str  # "pergunta" | "checklist" | "relatorio_checklist" | "outro"
    dados_extraidos: dict | None
    data_contexto: str | None  # Data focada na conversa atual

    # Saída
    resposta: str


# ============================================================
# 2. FUNÇÕES AUXILIARES
# ============================================================

def _obter_data_hoje() -> str:
    """Retorna a data de hoje em São Paulo no formato ISO (YYYY-MM-DD)."""
    fuso = pytz.timezone("America/Sao_Paulo")
    return datetime.now(fuso).strftime("%Y-%m-%d")


def _obter_datetime_formatado() -> str:
    """Retorna data e hora de São Paulo formatada para o prompt."""
    fuso = pytz.timezone("America/Sao_Paulo")
    return datetime.now(fuso).strftime("%d/%m/%Y %H:%M")


def construir_prompt_sistema(crianca_id: str, perfil_usuario: str, nome_usuario: str, especialidade: str = "") -> str:
    """Gera o System Prompt base do Manolo."""
    perfil_vivo = obter_perfil_vivo(crianca_id)
    hoje = _obter_datetime_formatado()
    primeiro_nome = nome_usuario.split()[0] if nome_usuario else ""

    prompt = f"""Você é o Manolo, assistente de acompanhamento do desenvolvimento infantil.
Data e hora atual em São Paulo: {hoje}. Use isso para resolver referências como 'hoje', 'ontem', 'essa semana'.

O nome do usuário atual é {primeiro_nome}. Use o nome dele na primeira mensagem da conversa.

PERFIL ATUAL DA CRIANÇA:
{perfil_vivo}

Você tem acesso ao histórico completo: laudos, relatórios de sessão,
avaliações padronizadas e registros diários (fornecidos via contexto).

Ao responder:
- Seja específico e cite datas quando relevante
- Identifique padrões e tendências ao longo do tempo
- Baseie-se estritamente no contexto fornecido nas mensagens para falar do histórico.
- Responda em português, de forma clara e acolhedora para a família.
- REGRA DE SEGURANÇA (ESCOPO): Se a pergunta NÃO tiver absolutamente nenhuma relação com a criança, desenvolvimento infantil, saúde ou rotina da família (ex: receitas culinárias, curiosidades, programação, etc.), você DEVE recusar educadamente a resposta, lembrando o usuário de que seu propósito é focado no acompanhamento da criança.
- REGRA CLÍNICA (DIAGNÓSTICOS): Você é um assistente de coleta de dados e acompanhamento. Você NUNCA DEVE EMITIR DIAGNÓSTICOS MÉDICOS, PSICOLÓGICOS OU PSIQUIÁTRICOS (ex: Autismo, TDAH, etc) sob nenhuma circunstância. Se questionado sobre suspeitas de diagnósticos, afirme claramente que não pode diagnosticar, recomende a busca por um profissional de saúde qualificado (médico, neuropediatra, terapeuta) e ofereça a geração de um relatório com o histórico de dados para a família levar à consulta.
- REGRA DE CONTEXTO (RAG): O 'Perfil Atual da Criança' (Perfil Vivo) contém características GERAIS e atemporais da criança. Os 'Registros diários (Checklists)' contêm os eventos ESPECÍFICOS que aconteceram naqueles dias. Ao responder perguntas sobre o que ocorreu em dias específicos (ex: "o que ele comeu ontem?", "nos últimos dias"), baseie-se ÚNICA E EXCLUSIVAMENTE nos Registros Diários. NUNCA misture as preferências gerais do Perfil Vivo como se fossem eventos que acabaram de acontecer.

Perfil do usuário atual: {perfil_usuario}
Especialidade (se terapeuta): {especialidade}
"""

    if perfil_usuario in ["família", "admin"]:
        prompt += "\nUse linguagem calorosa, cotidiana, sem jargão clínico."
    elif perfil_usuario == "terapeuta":
        prompt += "\nUse linguagem técnica e objetiva, com terminologia clínica apropriada."

    return prompt


# ============================================================
# 3. NÓS DO GRAFO
# ============================================================

@traceable(name="classificar_intencao")
def classificar_intencao(state: ManoloState) -> dict:
    """
    NÓ 1 — Determina se o usuário quer conversar (RAG) ou informar um evento diário (Checklist).
    """
    logger.info(f"[ROUTING] Iniciando classificação usando modelo: {settings.LLM_MODEL_ROUTING}")
    
    mensagem = state["mensagem"]

    client = get_openai_client()
    try:
        # Evita erro 400 em modelos de raciocínio (gpt-5, o1, o3) que não suportam temperature
        kwargs = {"temperature": 0} if "gpt-4" in settings.LLM_MODEL_ROUTING else {}

        response = client.chat.completions.create(
            model=settings.LLM_MODEL_ROUTING,
            messages=[
                {"role": "system", "content": """Você é um classificador de intenção para um assistente de desenvolvimento infantil.
Analise a mensagem do usuário e classifique ESTRITAMENTE em uma destas opções:
- 'relatorio_checklist': se o usuário estiver pedindo um resumo, relatório, ou perguntando "o que eu já anotei hoje?", "resumo do dia".
- 'pergunta': se o usuário está fazendo uma pergunta geral, pedindo conselho, ou consultando o histórico ("o que ele costuma comer?", "o que fazer se ele chorar?").
- 'checklist': se o usuário está relatando eventos do dia da criança de forma detalhada ou espontânea ("hoje ele comeu bem", "dormiu mal").
- 'outro': saudação simples, conversa fiada sem dados.

Responda APENAS com a palavra da classificação."""},
                {"role": "user", "content": mensagem},
            ],
            **kwargs
        )
        intencao = response.choices[0].message.content.strip().lower()
        if intencao not in ("pergunta", "checklist", "relatorio_checklist", "outro"):
            intencao = "checklist"  # fallback seguro para extração se houver dados
        return {"intencao": intencao}
    except Exception as e:
        logger.error(f"[CLASSIFICAR INTENÇÃO] Erro: {e}")
        return {"intencao": "checklist"}


@traceable(name="extrair_checklist_silencioso")
def extrair_checklist_silencioso(state: ManoloState) -> dict:
    """
    NÓ 2 — Executado apenas se a intenção for 'checklist'.
    Extrai JSON e salva no banco.
    Não responde nada (retorna string vazia) a menos que haja ambiguidade.
    """
    mensagem = state["mensagem"]
    crianca_id = state["crianca_id"]
    usuario_id = state["usuario_id"]
    
    fuso = pytz.timezone("America/Sao_Paulo")
    data_hoje = datetime.now(fuso).strftime("%Y-%m-%d")
    hora_atual = datetime.now(fuso).strftime("%H:%M")
    dia_semana_atual = datetime.now(fuso).strftime("%A")

    dias_pt = {"Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira", 
               "Thursday": "Quinta-feira", "Friday": "Sexta-feira", "Saturday": "Sábado", "Sunday": "Domingo"}
    dia_semana_pt = dias_pt.get(dia_semana_atual, dia_semana_atual)

    client = get_openai_client()

    prompt_extracao = f"""Você é um extrator de dados de rotina infantil.
Analise a mensagem do usuário.
A data de hoje em São Paulo é {data_hoje} ({dia_semana_pt}). O horário atual é {hora_atual}.

REGRAS DE DATA E CONTEXTO:
- NUNCA infira que um evento foi "ontem" ou outra data apenas porque o usuário usou o passado ("ele dormiu mal").
- Sempre que a data não for EXPLÍCITA, retorne data_referencia_iso = null (assumiremos hoje).
- Se a mensagem descrever eventos de múltiplos dias explicitamente, crie múltiplos itens na lista 'relatos'.
- AMBIGUIDADE (CONFIRMAÇÃO): Marque 'data_ambigua = True' APENAS se o usuário mencionar um dia vago E O CONTEXTO FOR IMPOSSÍVEL DE DEDUZIR.
- Se o usuário disser "comeu maçã", e você não souber se foi café ou almoço, anote no campo 'notas' da alimentação.

REGRAS DE DUPLA EXTRAÇÃO (TERAPEUTAS):
- Se o usuário atual for um terapeuta, foque em preencher a lista 'sessoes_terapia' com os detalhes da sessão (horários, notas clínicas, especialidade).
- SIMULTANEAMENTE, extraia TODOS os comportamentos descritos (mesmo os que pareçam rotineiros) e distribua-os nas categorias apropriadas. Exemplos:
  - "Colaborou com a troca da fralda" -> vestuario.colaborou_roupa = True
  - Engajamento motor -> movimento.atividades
  - Brinquedos usados -> brincar.com_que_brincou
- O terapeuta NÃO precisa relatar comportamentos domésticos. Deixe como null apenas o que não for dito, mas extraia rigorosamente tudo o que for relatado!"""

    try:
        response = client.beta.chat.completions.parse(
            model=settings.LLM_MODEL_EXTRACTION,
            response_format=LLMChecklistResponse,
            messages=[
                {"role": "system", "content": prompt_extracao},
                {"role": "user", "content": mensagem},
            ],
            temperature=0,
        )
        resultado = response.choices[0].message.parsed
        
        nova_data_contexto = state.get("data_contexto") or data_hoje
        resposta = ""  # Silencioso por padrão

        if resultado.contem_dados:
            logger.info(f"[EXTRAÇÃO SILENCIOSA] Dados detectados.")
            
            if resultado.correcao_retroativa and resultado.data_destino_correcao:
                logger.info(f"[CORREÇÃO RETROATIVA] Movendo registros de {nova_data_contexto} para {resultado.data_destino_correcao}")
                mesclar_checklists(crianca_id, nova_data_contexto, resultado.data_destino_correcao)
                nova_data_contexto = resultado.data_destino_correcao
                
                from datetime import datetime as dt
                try:
                    dt_fmt = dt.strptime(resultado.data_destino_correcao, "%Y-%m-%d").strftime("%d/%m/%Y")
                except:
                    dt_fmt = resultado.data_destino_correcao
                resposta = f"Ops, entendi perfeitamente! Já peguei os registros e movi tudo para o dia {dt_fmt}."
            
            elif resultado.data_ambigua:
                logger.info("[EXTRAÇÃO SILENCIOSA] Data/Contexto ambíguo detectado.")
                resposta = "Anotado! Só me confirma uma coisa: em qual dia exatamente isso aconteceu? Assim eu guardo na caixinha certa. 🥰"
            else:
                # Salva no banco (Extração Silenciosa)
                for relato in resultado.relatos:
                    data_ref = relato.data_referencia_iso or nova_data_contexto
                    nova_data_contexto = data_ref
                    
                    analise_json = relato.model_dump_json()
                    salvar_checklist(crianca_id, usuario_id, data_ref, "whatsapp_texto", analise_json)

                resposta = "Anotado! ✅"
            
            return {
                "dados_extraidos": resultado.model_dump(mode='json'),
                "data_contexto": nova_data_contexto,
                "resposta": resposta
            }
        else:
            if not resposta:
                resposta = "Desculpe, não consegui identificar dados de rotina na sua mensagem. Pode me contar com mais detalhes?"
            return {"dados_extraidos": None, "resposta": resposta}

    except Exception as e:
        logger.error(f"[EXTRAÇÃO SILENCIOSA] Erro: {e}")
        return {"dados_extraidos": None, "resposta": ""}


@traceable(name="responder_pergunta_rag")
def responder_pergunta_rag(state: ManoloState) -> dict:
    """
    NÓ 3 — Fluxo de pergunta livre: busca contexto RAG, monta prompt e chama LLM.
    """
    logger.info(f"[RAG] Iniciando resposta usando o modelo: {settings.LLM_MODEL_RAG}")
    
    mensagem = state["mensagem"]
    crianca_id = state["crianca_id"]
    nome_usuario = state["nome_usuario"]
    perfil_usuario = state["perfil_usuario"]

    client = get_openai_client()

    try:
        contexto_docs = buscar_contexto_documentos(mensagem, crianca_id)
        contexto_checklists = buscar_contexto_checklists(crianca_id)
    except Exception as e:
        logger.error(f"[RAG] Erro ao buscar dados do banco: {e}")
        return {"resposta": "Tive um problema ao buscar o histórico. Tente novamente.\n— Manolo"}

    prompt_sistema = construir_prompt_sistema(crianca_id, perfil_usuario, nome_usuario)
    
    # Suporte A/B Testing
    if "gpt-4" in settings.LLM_MODEL_RAG:
        regras_ancoragem = (
            f"REGRA ANTI-ALUCINAÇÃO: Se os registros diários acima estiverem vazios ou não contiverem"
            f" informações sobre o período específico perguntado, informe que não há registros para"
            f" esse período. NÃO use as preferências gerais do Perfil Vivo como substituto de eventos"
            f" reais. NÃO invente ou assuma que algo aconteceu.\n\n"
        )
        kwargs = {"temperature": 0.2}
    else:
        # Prompt otimizado para reasoning (família GPT-5, o1, o3)
        regras_ancoragem = (
            f"Use estritamente os registros diários acima para responder. Caso não haja dados no "
            f"contexto para o período solicitado, informe educadamente que não há registros.\n\n"
        )
        kwargs = {}

    prompt_usuario = (
        f"Contexto de documentos e laudos históricos:\n{contexto_docs}\n\n"
        f"Últimos registros diários (Checklists):\n{contexto_checklists}\n\n"
        f"{regras_ancoragem}"
        f"Pergunta do usuário: {mensagem}"
    )

    try:
        response = client.chat.completions.create(
            model=settings.LLM_MODEL_RAG,
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario},
            ],
            **kwargs
        )
        return {"resposta": response.choices[0].message.content}
    except Exception as e:
        logger.error(f"[RAG] Erro na chamada LLM: {e}")
        return {"resposta": "Não consegui processar sua mensagem agora. Tente novamente.\n— Manolo"}


@traceable(name="gerar_relatorio_checklist_node")
def gerar_relatorio_checklist_node(state: ManoloState) -> dict:
    """
    NÓ 4 — Relatório do Checklist sob demanda.
    Extrai a data da mensagem do usuário (se fornecida) antes de consultar o banco.
    """
    import re
    crianca_id = state["crianca_id"]
    mensagem = state["mensagem"]

    hoje = _obter_data_hoje()
    client = get_openai_client()

    # Usa o LLM para interpretar datas relativas ("ontem", "anteontem") ou absolutas
    try:
        resp_data = client.chat.completions.create(
            model=settings.LLM_MODEL_REPORT_DATE,
            messages=[
                {"role": "system", "content": f"A data de hoje é {hoje}. O usuário está pedindo um relatório. Extraia a qual data ele se refere na mensagem. Responda APENAS com a data no formato YYYY-MM-DD. Se ele não mencionar nenhuma data, responda HOJE."},
                {"role": "user", "content": mensagem}
            ],
            temperature=0
        )
        data_extraida = resp_data.choices[0].message.content.strip()
        
        if re.match(r'^\d{4}-\d{2}-\d{2}$', data_extraida):
            data_alvo = data_extraida
        else:
            data_alvo = state.get("data_contexto") or hoje
    except Exception as e:
        logger.error(f"[RELATÓRIO] Erro ao extrair data com LLM: {e}")
        data_alvo = state.get("data_contexto") or hoje

    logger.info(f"[RELATÓRIO] Gerando checklist para data: {data_alvo}")
    resumo_formatado = formatar_resumo_diario(crianca_id, data_alvo)

    # Pegamos a string do resumo formatado, jogamos no LLM e pedimos a "historinha calorosa"
    client = get_openai_client()
    nome_usuario = state.get("nome_usuario", "Família")
    perfil_usuario = state.get("perfil_usuario", "família")
    prompt_sistema = construir_prompt_sistema(crianca_id, perfil_usuario, nome_usuario)
    
    if perfil_usuario == "terapeuta":
        prompt_usuario = f"Com base APENAS neste checklist estruturado, escreva um resumo técnico e objetivo focado na evolução clínica, comportamentos e terapias realizadas.\n\n{resumo_formatado}"
    else:
        prompt_usuario = f"Com base APENAS neste checklist estruturado, escreva até dois parágrafos bem calorosos e empáticos para a família resumindo como foi o dia da criança.\n\n{resumo_formatado}"
    
    
    try:
        response = client.chat.completions.create(
            model=settings.LLM_MODEL_REPORT_SUMMARY,
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario}
            ],
            temperature=0.5
        )
        historinha = response.choices[0].message.content.strip()
        resposta_final = f"{historinha}\n\n---\n\n{resumo_formatado}"
    except Exception as e:
        logger.error(f"[RELATÓRIO] Erro ao gerar historinha: {e}")
        resposta_final = resumo_formatado

    return {"resposta": resposta_final}


# ============================================================
# 4. ROTEAMENTO CONDICIONAL
# ============================================================

def rotear_por_intencao(state: ManoloState) -> str:
    """Função de roteamento a partir do Nó de Classificação."""
    intencao = state.get("intencao", "outro")
    
    if intencao == "checklist":
        return "extrair_silencioso"
    elif intencao == "relatorio_checklist":
        return "relatorio_checklist"
    else:
        return "rag"



# ============================================================
# 5. CONSTRUÇÃO E COMPILAÇÃO DO GRAFO
# ============================================================

graph_builder = StateGraph(ManoloState)

# Adicionar nós
graph_builder.add_node("classificar", classificar_intencao)
graph_builder.add_node("extrair_silencioso", extrair_checklist_silencioso)
graph_builder.add_node("rag", responder_pergunta_rag)
graph_builder.add_node("relatorio_checklist", gerar_relatorio_checklist_node)

# Definir fluxo
graph_builder.set_entry_point("classificar")
graph_builder.add_conditional_edges("classificar", rotear_por_intencao, {
    "extrair_silencioso": "extrair_silencioso",
    "rag": "rag",
    "relatorio_checklist": "relatorio_checklist",
    "fim": END
})
graph_builder.add_edge("extrair_silencioso", END)
graph_builder.add_edge("rag", END)
graph_builder.add_edge("relatorio_checklist", END)

# Compilar com checkpointer em memória (thread_id = telefone do usuário)
memory = MemorySaver()
manolo_graph = graph_builder.compile(checkpointer=memory)


# ============================================================
# 6. PONTO DE ENTRADA PARA O WEBHOOK
# ============================================================

def executar_grafo(
    mensagem: str,
    telefone: str,
    usuario_id: str,
    nome_usuario: str,
    perfil_usuario: str,
    crianca_id: str,
) -> str:
    """
    Ponto de entrada único chamado pelo webhook do WhatsApp.
    Executa o grafo completo e retorna a resposta final.
    """
    config = {"configurable": {"thread_id": telefone}}

    # Recuperar data_contexto do estado anterior (se houver)
    data_contexto_anterior = _obter_data_hoje()
    
    try:
        estado_anterior = manolo_graph.get_state(config)
        if estado_anterior and estado_anterior.values:
            if estado_anterior.values.get("data_contexto"):
                data_contexto_anterior = estado_anterior.values.get("data_contexto")
    except Exception:
        pass  # Sem estado anterior, segue normalmente

    resultado = manolo_graph.invoke(
        {
            "mensagem": mensagem,
            "telefone": telefone,
            "usuario_id": usuario_id,
            "nome_usuario": nome_usuario,
            "perfil_usuario": perfil_usuario,
            "crianca_id": crianca_id,
            "intencao": "",
            "dados_extraidos": None,
            "data_contexto": data_contexto_anterior,
            "resposta": "",
        },
        config,
    )

    resposta = resultado.get("resposta", "Desculpe, não consegui processar sua mensagem.")

    # Disparar atualização de perfil em background se houve dados extraídos
    if resultado.get("dados_extraidos"):
        try:
            atualizar_perfil(crianca_id)
        except Exception as e:
            logger.error(f"Erro ao atualizar perfil em background: {e}")

    return resposta