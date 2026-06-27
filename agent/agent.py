"""Orquestração do agente (LangGraph) e contexto."""

import logging
from datetime import datetime
import pytz
from core.memory import buscar_contexto_documentos, obter_perfil_vivo, buscar_contexto_checklists
from agent.profile import atualizar_perfil
from core.clients import get_openai_client

logger = logging.getLogger(__name__)

# Histórico de conversas em memória (substituído por Redis/BD em produção)
conversation_history = {}

def construir_prompt_sistema(crianca_id: str, perfil_usuario: str, nome_usuario: str, especialidade: str = "") -> str:
    """Gera o System Prompt base do Manolo (conforme definido no MANOLO.md)."""
    perfil_vivo = obter_perfil_vivo(crianca_id)

    # Adiciona data e hora
    fuso = pytz.timezone('America/Sao_Paulo')
    hoje = datetime.now(fuso).strftime('%d/%m/%Y %H:%M')

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

    # Adiciona tom por perfil
    if perfil_usuario in ['família', 'admin']:
        prompt += "\nUse linguagem calorosa, cotidiana, sem jargão clínico."
    elif perfil_usuario == 'terapeuta':
        prompt += "\nUse linguagem técnica e objetiva, com terminologia clínica apropriada."

    return prompt

def perguntar_ao_manolo(pergunta: str, crianca_id: str, telefone_whatsapp: str, nome_usuario: str, perfil_usuario: str = "pai/mãe") -> str:
    """Fluxo principal de perguntas: RAG + Chamada do LLM com histórico de conversa."""
    try:
        client = get_openai_client()

        # Obter histórico do usuário
        user_history = conversation_history.get(telefone_whatsapp, [])

        precisa_atualizar_perfil = "atualize o perfil" in pergunta.lower() or "atualizar perfil" in pergunta.lower()
        if precisa_atualizar_perfil:
            logger.info("Solicitação explícita para atualizar o perfil detectada.")

        # Bloco de try/except para erros de banco
        try:
            contexto_docs = buscar_contexto_documentos(pergunta, crianca_id)
            contexto_checklists = buscar_contexto_checklists(crianca_id)
        except Exception as e:
            logger.error(f"Erro ao buscar dados do banco: {e}")
            return "Tive um problema ao buscar o histórico. Tente novamente.\n— Manolo"

        prompt_sistema = construir_prompt_sistema(crianca_id, perfil_usuario, nome_usuario)

        prompt_usuario = f"Contexto de documentos e laudos históricos:\n{contexto_docs}\n\nÚltimos registros diários (Checklists):\n{contexto_checklists}\n\nPergunta do usuário: {pergunta}"

        messages = [{"role": "system", "content": prompt_sistema}]
        messages.extend(user_history)
        messages.append({"role": "user", "content": prompt_usuario})

        # Bloco de try/except para erros de LLM
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.2
        )
        resposta_final = response.choices[0].message.content

        user_history.append({"role": "user", "content": pergunta})
        user_history.append({"role": "assistant", "content": resposta_final})

        conversation_history[telefone_whatsapp] = user_history[-10:]

        if precisa_atualizar_perfil:
            logger.info("Disparando atualização do perfil em segundo plano...")
            atualizar_perfil(crianca_id)

        return resposta_final
    except Exception as e:
        logger.error(f"Erro ao chamar LLM: {e}")
        return "Não consegui processar sua mensagem agora. Tente novamente em alguns instantes.\n— Manolo"