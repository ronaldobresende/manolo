"""Orquestração do agente (LangGraph) e contexto."""

import logging
from core.memory import buscar_contexto_documentos, obter_perfil_vivo, buscar_contexto_checklists
# A importação de 'atualizar_perfil' estava sendo sobrescrita por uma variável.
from agent.profile import atualizar_perfil
from core.clients import get_openai_client

logger = logging.getLogger(__name__)

# Histórico de conversas em memória (substituído por Redis/BD em produção)
conversation_history = {}

def construir_prompt_sistema(crianca_id: str, perfil_usuario: str, especialidade: str = "") -> str:
    """Gera o System Prompt base do Manolo (conforme definido no MANOLO.md)."""
    perfil_vivo = obter_perfil_vivo(crianca_id)
    
    prompt = f"""Você é o Manolo, assistente de acompanhamento do desenvolvimento infantil.

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
    return prompt

def perguntar_ao_manolo(pergunta: str, crianca_id: str, telefone_whatsapp: str, perfil_usuario: str = "pai/mãe") -> str:
    """Fluxo principal de perguntas: RAG + Chamada do LLM com histórico de conversa."""
    client = get_openai_client()
    
    # Obter histórico do usuário
    user_history = conversation_history.get(telefone_whatsapp, [])

    # Variável renomeada para evitar conflito com a função importada 'atualizar_perfil'
    precisa_atualizar_perfil = False
    if "atualize o perfil" in pergunta.lower() or "atualizar perfil" in pergunta.lower():
        logger.info("Solicitação explícita para atualizar o perfil detectada.")
        precisa_atualizar_perfil = True

    contexto_docs = buscar_contexto_documentos(pergunta, crianca_id)
    contexto_checklists = buscar_contexto_checklists(crianca_id)
    prompt_sistema = construir_prompt_sistema(crianca_id, perfil_usuario)
    
    prompt_usuario = f"Contexto de documentos e laudos históricos:\n{contexto_docs}\n\nÚltimos registros diários (Checklists):\n{contexto_checklists}\n\nPergunta do usuário: {pergunta}"
    
    # Monta o payload de mensagens com o histórico
    messages = [{"role": "system", "content": prompt_sistema}]
    messages.extend(user_history)
    messages.append({"role": "user", "content": prompt_usuario})

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.2  # Reduzido de 0.7 para 0.2 para maior precisão
        )
        resposta_final = response.choices[0].message.content

        # Atualiza o histórico com a pergunta atual e a resposta
        user_history.append({"role": "user", "content": pergunta})
        user_history.append({"role": "assistant", "content": resposta_final})
        
        # Mantém apenas as últimas 10 mensagens
        conversation_history[telefone_whatsapp] = user_history[-10:]

        # Atualiza o perfil em segundo plano se a flag foi ativada
        if precisa_atualizar_perfil:
            logger.info("Disparando atualização do perfil em segundo plano...")
            atualizar_perfil(crianca_id)

        return resposta_final
    except Exception as e:
        logger.error(f"Erro ao chamar LLM: {e}")
        return "Desculpe, ocorreu um erro ao tentar processar sua pergunta."