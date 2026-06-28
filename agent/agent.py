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
    salvar_campo_individual,
    buscar_campos_ausentes,
    obter_checklist_id_do_dia,
    CAMPO_CONFIG,
    _obter_ou_criar_checklist,
    mesclar_checklists
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

@traceable(name="extrair_checklist_silencioso")
def extrair_checklist_silencioso(state: ManoloState) -> dict:
    """
    NÓ 1 — Analisa toda mensagem recebida.
    Se contiver dados de rotina da criança, extrai JSON (podendo fatiar em múltiplos dias) e salva no banco.
    Trata correção retroativa de datas.
    """
    mensagem = state["mensagem"]
    crianca_id = state["crianca_id"]
    usuario_id = state["usuario_id"]
    data_hoje = _obter_data_hoje()
    dia_semana_atual = datetime.now(pytz.timezone("America/Sao_Paulo")).strftime("%A")

    # Mapeamento do dia da semana pra pt-br
    dias_pt = {"Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira", 
               "Thursday": "Quinta-feira", "Friday": "Sexta-feira", "Saturday": "Sábado", "Sunday": "Domingo"}
    dia_semana_pt = dias_pt.get(dia_semana_atual, dia_semana_atual)

    client = get_openai_client()

    prompt_extracao = f"""Você é um extrator de dados de rotina infantil.
Analise a mensagem do usuário. Se contiver QUALQUER informação sobre a rotina diária, extraia os dados.
A data de hoje é {data_hoje} ({dia_semana_pt}).

REGRAS DE DATA:
- Se a mensagem não mencionar data NENHUMA, não preencha a data do relato (retorne null) para usarmos o contexto atual.
- Se a mensagem descrever eventos de MÚLTIPLOS dias (ex: "sábado fez x, ontem fez y, hoje z"), crie múltiplos itens na lista 'relatos'.
- MATEMÁTICA DE DATAS: Se o usuário mencionar um dia da semana (ex: 'segunda', 'domingo'), calcule DE CABEÇA a data ISO correta do passado mais recente para esse dia, baseando-se em hoje ({data_hoje}).
- CORREÇÃO RETROATIVA: Se o usuário estiver explicitamente dizendo que as mensagens dele anteriores eram de OUTRO dia (ex: "errei, aquilo era de ontem", "as infos são do dia 27"), marque correcao_retroativa = True e defina data_destino_correcao."""

    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            response_format=LLMChecklistResponse,
            messages=[
                {"role": "system", "content": prompt_extracao},
                {"role": "user", "content": mensagem},
            ],
            temperature=0,
        )
        resultado = response.choices[0].message.parsed
        
        # Variável para propagar a nova data focada
        nova_data_contexto = state.get("data_contexto") or data_hoje

        if resultado.contem_dados:
            logger.info(f"[EXTRAÇÃO SILENCIOSA] Dados de rotina detectados na mensagem.")
            
            if resultado.correcao_retroativa and resultado.data_destino_correcao:
                # O usuário pediu para corrigir a data retroativamente!
                logger.info(f"[CORREÇÃO RETROATIVA] Movendo registros de {nova_data_contexto} para {resultado.data_destino_correcao}")
                mesclar_checklists(crianca_id, nova_data_contexto, resultado.data_destino_correcao)
                nova_data_contexto = resultado.data_destino_correcao
            
            elif resultado.data_ambigua:
                logger.info("[EXTRAÇÃO SILENCIOSA] Data ambígua detectada. Aguardando esclarecimento.")
                # Não salva nada, só avisa a ambiguidade
            else:
                # Salva cada relato extraído silenciosamente no banco
                for relato in resultado.relatos:
                    data_ref = relato.data_referencia_iso or nova_data_contexto
                    nova_data_contexto = data_ref  # A última data mencionada vira o novo contexto âncora
                    
                    analise_json = relato.model_dump_json()
                    salvar_checklist(crianca_id, usuario_id, data_ref, "whatsapp_texto", analise_json)
            
            return {
                "dados_extraidos": resultado.model_dump(mode='json'),
                "data_contexto": nova_data_contexto
            }
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
    NÓ 4 — Relato espontâneo. Gera uma resposta amigável e trata correções de datas ou ambiguidades.
    """
    mensagem = state["mensagem"]
    nome_usuario = state["nome_usuario"]
    data_hoje = _obter_data_hoje()
    
    dados = state.get("dados_extraidos", {})
    if not dados:
        dados = {}

    client = get_openai_client()

    # 1. Tratar Ambiguidade de Data
    if dados.get("data_ambigua"):
        return {"resposta": "Que ótimo saber disso! 🥰 Você consegue me dizer mais ou menos qual dia foi isso, para eu anotar certinho na rotina?"}

    # 2. Tratar Correção Retroativa
    if dados.get("correcao_retroativa") and dados.get("data_destino_correcao"):
        data_destino = dados["data_destino_correcao"]
        
        from datetime import datetime
        try:
            dt = datetime.strptime(data_destino, "%Y-%m-%d").strftime("%d/%m/%Y")
        except:
            dt = data_destino
            
        return {"resposta": f"Ops, entendi perfeitamente! Já peguei os registros e movi tudo para o dia {dt}. Tudo certo por aqui! Tem mais alguma coisa desse dia que você queira adicionar? 📝"}

    # 3. Relato Normal (Agradecimento empático)
    # Pega as datas que foram extraídas na mensagem atual
    datas_extraidas = set()
    if dados.get("relatos"):
        for relato in dados["relatos"]:
            if relato.get("data_referencia_iso"):
                datas_extraidas.add(relato["data_referencia_iso"])
    
    # Se o LLM não extraiu data, assume a data de contexto ancorada
    data_ancorada = state.get("data_contexto") or data_hoje
    if not datas_extraidas:
        datas_extraidas.add(data_ancorada)

    # Formatar as datas para o texto (ex: "hoje (28/06)" ou "dia 27/06")
    from datetime import datetime, timedelta
    dt_hoje = datetime.strptime(data_hoje, "%Y-%m-%d")
    ontem = (dt_hoje - timedelta(days=1)).strftime("%Y-%m-%d")

    periodos = []
    for d_iso in sorted(datas_extraidas):
        try:
            d_fmt = datetime.strptime(d_iso, "%Y-%m-%d").strftime("%d/%m/%Y")
            if d_iso == data_hoje:
                periodos.append(f"hoje ({d_fmt})")
            elif d_iso == ontem:
                periodos.append(f"ontem ({d_fmt})")
            else:
                periodos.append(f"dia {d_fmt}")
        except Exception:
            periodos.append(d_iso)
            
    periodo_texto = " e ".join(periodos)

    prompt_empatia = f"""A mãe enviou um relato livre sobre a rotina da criança:
"{mensagem}"

Você já extraiu silenciosamente e guardou esses dados no banco para o(s) período(s): {periodo_texto}.
Sua tarefa é gerar uma resposta curta (máximo 2 parágrafos), acolhedora e empática.
Valide eventuais sentimentos, dificuldades ou conquistas citadas de forma natural.
Finalize a mensagem apenas confirmando de forma sutil: "Anotei as informações para [periodo_texto] ✅" (para que a mãe saiba qual dia o sistema deduziu).
NÃO faça perguntas investigativas, o sistema já fará isso depois se necessário."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt_empatia}],
            temperature=0.7,
        )
        resposta = response.choices[0].message.content
    except Exception as e:
        logger.error(f"[CHECKLIST COMPLETO] Erro na geração empática: {e}")
        resposta = f"Obrigado pelo relato, {nome_usuario}! Registrei as informações para {periodo_texto}. ✅"

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

    MAPA_SCHEMAS = {
        "sono": SonoModel, "humor": HumorModel, "comunicacao": ComunicacaoModel,
        "alimentacao": AlimentacaoModel, "brincar": BrincarModel, "higiene": HigieneModel,
        "movimento": MovimentoModel, "vestuario": VestuarioModel, "tela": TelaModel, "rotina": RotinaModel
    }

    # Estrutura a resposta como dados do campo pendente
    prompt = f"""O usuário respondeu à pergunta sobre '{campo_pendente}' da rotina da criança.
Extraia os dados estruturados relevantes para esse campo específico.
Se não houver dados estruturados compatíveis, faça o melhor esforço e preencha as notas."""

    try:
        schema_model = MAPA_SCHEMAS.get(campo_pendente)
        if schema_model:
            response = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                response_format=schema_model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": mensagem},
                ],
                temperature=0,
            )
            dados_campo = response.choices[0].message.parsed.model_dump(mode='json')
        else:
            dados_campo = {"notas": mensagem}

        # Salvar no banco usando data_contexto
        data_ancorada = state.get("data_contexto") or data_hoje
        checklist_id = obter_checklist_id_do_dia(crianca_id, data_ancorada)
        if not checklist_id:
            checklist_id = _obter_ou_criar_checklist(crianca_id, usuario_id, data_ancorada, "whatsapp_texto")

        salvar_campo_individual(checklist_id, campo_pendente, dados_campo)

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
    
    # Se a intenção era corrigir data de forma retroativa, pula a cobrança pra focar só no "CTRL+Z"
    dados = state.get("dados_extraidos", {})
    if dados and dados.get("correcao_retroativa") and dados.get("data_destino_correcao"):
        return {"resposta": resposta_atual, "campo_pendente": None}
    
    # Se era uma data ambígua aguardando resposta, pula a cobrança
    if dados and dados.get("data_ambigua"):
        return {"resposta": resposta_atual, "campo_pendente": None}

    # Verifica na data_contexto (ou hoje se não houver contexto)
    data_ancorada = state.get("data_contexto") or data_hoje

    try:
        campos_ausentes = buscar_campos_ausentes(crianca_id, data_ancorada)

        if campos_ausentes:
            proximo_campo = campos_ausentes[0]
            config = CAMPO_CONFIG.get(proximo_campo, {})
            pergunta_template = config.get("pergunta", f"Como foi {proximo_campo}?")

            pergunta = pergunta_template.replace("{da_crianca}", "do Bernardo")
            pergunta = pergunta.replace("{a_crianca}", "o Bernardo")
            
            # Ajustar texto de tempo para a pergunta
            if data_ancorada == data_hoje:
                pergunta = pergunta.replace("{periodo}", "hoje")
            else:
                from datetime import datetime, timedelta
                dt_hoje = datetime.strptime(data_hoje, "%Y-%m-%d")
                ontem = (dt_hoje - timedelta(days=1)).strftime("%Y-%m-%d")
                if data_ancorada == ontem:
                    pergunta = pergunta.replace("{periodo}", "ontem")
                else:
                    pergunta = pergunta.replace("{periodo}", f"no dia {datetime.strptime(data_ancorada, '%Y-%m-%d').strftime('%d/%m/%Y')}")

            client = get_openai_client()
            prompt_integracao = f"""Você é o Manolo, um assistente acolhedor de desenvolvimento infantil.
Você acabou de formular a seguinte resposta para a família:
"{resposta_atual}"

Sua tarefa agora é juntar a seguinte pergunta no final dessa resposta:
"{pergunta}"

OBRIGATÓRIO: Sua mensagem final DEVE terminar com a pergunta acima. Não engula, mude ou omita a pergunta, ela é essencial para a extração do banco.
Reescreva a transição para que fique um pouco mais fluida, mas a frase final deve ser a pergunta! Pode usar emojis."""

            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": prompt_integracao}],
                    temperature=0.6,
                )
                resposta_final = response.choices[0].message.content
            except Exception as e:
                logger.error(f"[COBRANÇA] Erro no LLM de integração: {e}")
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
        return "checklist"
    else:
        return "pergunta"



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
    data_contexto_anterior = _obter_data_hoje()
    
    try:
        estado_anterior = manolo_graph.get_state(config)
        if estado_anterior and estado_anterior.values:
            campo_pendente_anterior = estado_anterior.values.get("campo_pendente")
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
            "campo_pendente": campo_pendente_anterior,
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