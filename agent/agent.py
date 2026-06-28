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
from agent.checklist import (
    salvar_checklist,
    salvar_campo_individual,
    buscar_campos_ausentes,
    obter_checklist_id_do_dia,
    CAMPO_CONFIG,
    _obter_ou_criar_checklist,
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
    intencao: str  # "pergunta" | "checklist" | "resposta_pendencia" | ""
    dados_extraidos: dict | None
    campo_pendente: str | None  # Campo que o bot estava cobrando

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

    prompt = f"""Você é o Manolo, assistente de acompanhamento do desenvolvimento infantil.
Data e hora atual em São Paulo: {hoje}. Use isso para resolver referências como 'hoje', 'ontem', 'essa semana'.

O nome do usuário atual é {nome_usuario}. Use o nome dele na primeira mensagem da conversa.

PERFIL ATUAL DA CRIANÇA:
{perfil_vivo}

Você tem acesso ao histórico completo: laudos, relatórios de sessão,
avaliações padronizadas e registros diários (fornecidos via contexto).

Ao responder:
- Seja específico e cite datas quando relevante
- Identifique padrões e tendências ao longo do tempo
- Baseie-se estritamente no contexto fornecido nas mensagens para falar do histórico.
- Responda em português, de forma clara e acolhedora para a família.

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

@traceable(name="extrair_checklist_silencioso")
def extrair_checklist_silencioso(state: ManoloState) -> dict:
    """
    NÓ 1 — Analisa toda mensagem recebida.
    Se contiver dados de rotina da criança, extrai JSON e salva no banco.
    Não altera a resposta do bot.
    """
    mensagem = state["mensagem"]
    crianca_id = state["crianca_id"]
    usuario_id = state["usuario_id"]
    data_hoje = _obter_data_hoje()

    client = get_openai_client()

    prompt_extracao = """Você é um extrator silencioso de dados de rotina infantil.
Analise a mensagem do usuário. Se ela contiver QUALQUER informação sobre a rotina
diária da criança (sono, alimentação, humor, comunicação, brincar, higiene,
vestuário, movimento, tela, rotina/transições), extraia em JSON.

Retorne um JSON com a estrutura:
{
  "contem_dados": true/false,
  "campos_preenchidos": {
    "sono": {...} ou null,
    "humor": {...} ou null,
    "comunicacao": {...} ou null,
    "alimentacao": {...} ou null,
    "brincar": {...} ou null,
    "higiene": {...} ou null,
    "vestuario": {...} ou null,
    "movimento": {...} ou null,
    "tela": {...} ou null,
    "rotina": {...} ou null
  },
  "campos_ausentes": ["lista dos campos que NÃO foram mencionados"]
}

Se a mensagem NÃO contiver dados de rotina, retorne:
{"contem_dados": false, "campos_preenchidos": {}, "campos_ausentes": []}

Seja generoso na extração: se o usuário mencionar "dormiu bem", extraia como sono.
Se mencionar "comeu arroz", extraia como alimentação. Etc."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": prompt_extracao},
                {"role": "user", "content": mensagem},
            ],
            temperature=0,
        )
        resultado = json.loads(response.choices[0].message.content)

        if resultado.get("contem_dados"):
            logger.info(f"[EXTRAÇÃO SILENCIOSA] Dados de rotina detectados na mensagem.")
            # Salva silenciosamente no banco
            analise_json = json.dumps(resultado, ensure_ascii=False)
            salvar_checklist(crianca_id, usuario_id, data_hoje, "whatsapp_texto", analise_json)
            return {"dados_extraidos": resultado}
        else:
            logger.info("[EXTRAÇÃO SILENCIOSA] Nenhum dado de rotina na mensagem.")
            return {"dados_extraidos": None}

    except Exception as e:
        logger.error(f"[EXTRAÇÃO SILENCIOSA] Erro: {e}")
        return {"dados_extraidos": None}


@traceable(name="classificar_intencao")
def classificar_intencao(state: ManoloState) -> dict:
    """
    NÓ 2 — Determina a intenção da mensagem.
    Leva em conta se havia um campo_pendente (cobrança ativa anterior).
    """
    mensagem = state["mensagem"]
    campo_pendente = state.get("campo_pendente")

    # Se havia um campo sendo cobrado e a mensagem parece uma resposta
    # (não é uma pergunta explícita), trata como resposta à pendência
    if campo_pendente:
        client = get_openai_client()
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"""O bot tinha acabado de perguntar sobre '{campo_pendente}' da rotina da criança.
O usuário respondeu com a mensagem abaixo.
Classifique: é uma RESPOSTA à pergunta feita (sobre {campo_pendente}), ou é uma PERGUNTA NOVA sobre outro assunto?
Responda APENAS com: 'resposta_pendencia' ou 'pergunta'."""},
                    {"role": "user", "content": mensagem},
                ],
                temperature=0,
            )
            classificacao = response.choices[0].message.content.strip().lower()
            if "resposta_pendencia" in classificacao:
                return {"intencao": "resposta_pendencia"}
        except Exception as e:
            logger.error(f"[CLASSIFICAR INTENÇÃO] Erro na verificação de pendência: {e}")

    # Classificação geral
    client = get_openai_client()
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """Você é um classificador de intenção para um assistente de desenvolvimento infantil.
Analise a mensagem do usuário e classifique:
- 'pergunta': se o usuário está fazendo uma pergunta, pedindo informação ou conversando.
- 'checklist': se o usuário está relatando eventos do dia da criança de forma detalhada/espontânea.

Responda APENAS com: 'pergunta' ou 'checklist'."""},
                {"role": "user", "content": mensagem},
            ],
            temperature=0,
        )
        intencao = response.choices[0].message.content.strip().lower()
        if intencao not in ("pergunta", "checklist"):
            intencao = "pergunta"  # fallback seguro
        return {"intencao": intencao}
    except Exception as e:
        logger.error(f"[CLASSIFICAR INTENÇÃO] Erro: {e}")
        return {"intencao": "pergunta"}


@traceable(name="responder_pergunta_rag")
def responder_pergunta_rag(state: ManoloState) -> dict:
    """
    NÓ 3 — Fluxo de pergunta livre: busca contexto RAG, monta prompt e chama LLM.
    """
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
    prompt_usuario = (
        f"Contexto de documentos e laudos históricos:\n{contexto_docs}\n\n"
        f"Últimos registros diários (Checklists):\n{contexto_checklists}\n\n"
        f"Pergunta do usuário: {mensagem}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario},
            ],
            temperature=0.2,
        )
        return {"resposta": response.choices[0].message.content}
    except Exception as e:
        logger.error(f"[RAG] Erro na chamada LLM: {e}")
        return {"resposta": "Não consegui processar sua mensagem agora. Tente novamente.\n— Manolo"}


@traceable(name="processar_checklist_completo")
def processar_checklist_completo(state: ManoloState) -> dict:
    """
    NÓ 4 — Relato espontâneo longo. Estrutura e salva o checklist.
    """
    mensagem = state["mensagem"]
    crianca_id = state["crianca_id"]
    usuario_id = state["usuario_id"]
    nome_usuario = state["nome_usuario"]
    data_hoje = _obter_data_hoje()

    # A extração silenciosa (Nó 1) já salvou os dados.
    # Aqui geramos apenas uma resposta amigável de confirmação.
    dados = state.get("dados_extraidos")
    campos_salvos = []
    if dados and dados.get("campos_preenchidos"):
        campos_salvos = [k for k, v in dados["campos_preenchidos"].items() if v]

    if campos_salvos:
        campos_str = ", ".join(campos_salvos)
        resposta = f"Anotei as informações sobre {campos_str} para hoje ({data_hoje}). ✅"
    else:
        resposta = f"Obrigado pelo relato, {nome_usuario}! Registrei as informações para hoje. ✅"

    return {"resposta": resposta}


@traceable(name="processar_resposta_pendencia")
def processar_resposta_pendencia(state: ManoloState) -> dict:
    """
    NÓ 5 — Interpreta a resposta do usuário no contexto do campo_pendente.
    """
    mensagem = state["mensagem"]
    campo_pendente = state["campo_pendente"]
    crianca_id = state["crianca_id"]
    usuario_id = state["usuario_id"]
    nome_usuario = state["nome_usuario"]
    data_hoje = _obter_data_hoje()

    client = get_openai_client()

    # Estrutura a resposta como dados do campo pendente
    prompt = f"""O usuário respondeu à pergunta sobre '{campo_pendente}' da rotina da criança.
Extraia os dados relevantes para esse campo específico.
Retorne um JSON com a chave '{campo_pendente}' e os dados extraídos.
Se não conseguir extrair dados úteis, retorne {{"{campo_pendente}": "Resposta livre: <mensagem resumida>"}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": mensagem},
            ],
            temperature=0,
        )
        dados_campo = json.loads(response.choices[0].message.content)

        # Salvar no banco
        checklist_id = obter_checklist_id_do_dia(crianca_id, data_hoje)
        if not checklist_id:
            checklist_id = _obter_ou_criar_checklist(crianca_id, usuario_id, data_hoje, "whatsapp_texto")

        salvar_campo_individual(checklist_id, campo_pendente, dados_campo.get(campo_pendente, dados_campo))

        resposta = f"Anotei as informações sobre {campo_pendente}! 👍"
        return {"resposta": resposta, "campo_pendente": None}

    except Exception as e:
        logger.error(f"[RESPOSTA PENDÊNCIA] Erro: {e}")
        return {"resposta": f"Anotei sua resposta sobre {campo_pendente}, obrigado! 👍", "campo_pendente": None}


def verificar_e_cobrar_pendencia(state: ManoloState) -> dict:
    """
    NÓ 6 — Nó final. Verifica campos ausentes e anexa UMA pergunta conversacional.
    """
    crianca_id = state["crianca_id"]
    resposta_atual = state["resposta"]
    data_hoje = _obter_data_hoje()

    try:
        campos_ausentes = buscar_campos_ausentes(crianca_id, data_hoje)

        if campos_ausentes:
            proximo_campo = campos_ausentes[0]
            config = CAMPO_CONFIG.get(proximo_campo, {})
            pergunta_template = config.get("pergunta", f"Como foi {proximo_campo} hoje?")

            # Substituir placeholders
            # TODO: Buscar nome da criança do banco
            pergunta = pergunta_template.replace("{da_crianca}", "do Bernardo")
            pergunta = pergunta.replace("{a_crianca}", "o Bernardo")
            pergunta = pergunta.replace("{periodo}", "hoje")

            # Anexar pergunta à resposta com quebra de linha
            resposta_final = f"{resposta_atual}\n\n{pergunta}"

            logger.info(f"[COBRANÇA] Campo pendente: {proximo_campo}. Perguntando ao usuário.")
            return {"resposta": resposta_final, "campo_pendente": proximo_campo}
        else:
            logger.info("[COBRANÇA] Todos os campos do checklist de hoje estão preenchidos! 🎉")
            return {"resposta": resposta_atual, "campo_pendente": None}

    except Exception as e:
        logger.error(f"[COBRANÇA] Erro ao verificar pendências: {e}")
        return {"resposta": resposta_atual, "campo_pendente": None}


# ============================================================
# 4. ROTEAMENTO CONDICIONAL
# ============================================================

def rotear_por_intencao(state: ManoloState) -> str:
    """Função de roteamento: direciona para o nó correto com base na intenção."""
    intencao = state.get("intencao", "pergunta")
    if intencao == "resposta_pendencia":
        return "resposta_pendencia"
    elif intencao == "checklist":
        return "checklist_completo"
    else:
        return "rag"


# ============================================================
# 5. CONSTRUÇÃO E COMPILAÇÃO DO GRAFO
# ============================================================

graph_builder = StateGraph(ManoloState)

# Adicionar nós
graph_builder.add_node("extrair_silencioso", extrair_checklist_silencioso)
graph_builder.add_node("classificar", classificar_intencao)
graph_builder.add_node("rag", responder_pergunta_rag)
graph_builder.add_node("checklist_completo", processar_checklist_completo)
graph_builder.add_node("resposta_pendencia", processar_resposta_pendencia)
graph_builder.add_node("cobrar_pendencia", verificar_e_cobrar_pendencia)

# Definir fluxo
graph_builder.set_entry_point("extrair_silencioso")
graph_builder.add_edge("extrair_silencioso", "classificar")
graph_builder.add_conditional_edges("classificar", rotear_por_intencao, {
    "pergunta": "rag",
    "checklist": "checklist_completo",
    "resposta_pendencia": "resposta_pendencia",
})
graph_builder.add_edge("rag", "cobrar_pendencia")
graph_builder.add_edge("checklist_completo", "cobrar_pendencia")
graph_builder.add_edge("resposta_pendencia", "cobrar_pendencia")
graph_builder.add_edge("cobrar_pendencia", END)

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

    # Recuperar campo_pendente do estado anterior (se houver)
    campo_pendente_anterior = None
    try:
        estado_anterior = manolo_graph.get_state(config)
        if estado_anterior and estado_anterior.values:
            campo_pendente_anterior = estado_anterior.values.get("campo_pendente")
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
            "campo_pendente": campo_pendente_anterior,
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