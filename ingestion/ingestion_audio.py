"""Script para ingestão de áudios (checklists) via Whisper local e estruturação via LLM."""

import os
import argparse
import logging
import tempfile
from typing import Callable, Awaitable, Any
import json
from dotenv import load_dotenv
from core.database import get_connection
from agent.checklist import salvar_checklist
from agent.profile import atualizar_perfil
from core.clients import get_openai_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Hardcoded para a Fase 1
CRIANCA_ID = 'c0000000-0000-0000-0000-000000000001'

async def processar_midia_checklist(
    downloader: Callable[[str], Awaitable[None]],
    data_checklist: str,
    crianca_id: str,
    usuario_id: str,
    origem: str
) -> str | None:
    """
    Orquestra o download, processamento e limpeza de um arquivo de áudio.
    Esta função é agnóstica ao canal (Telegram, WhatsApp, etc).
    """
    audio_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".oga") as temp_audio:
            audio_path = temp_audio.name
        
        await downloader(audio_path)
        logger.info(f"Mídia baixada para o caminho temporário: {audio_path}")

        return _processar_arquivo_audio(audio_path, data_checklist, crianca_id, usuario_id, origem)

    except Exception as e:
        logger.error(f"Erro no fluxo de processamento de mídia: {e}")
        raise  # Relança a exceção para que o chamador (main.py) possa tratá-la
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
            logger.info(f"Arquivo de mídia temporário removido: {audio_path}")

def _determinar_intencao_audio(transcricao: str) -> str:
    """Usa o LLM para classificar a intenção do usuário (pergunta ou checklist)."""
    if not transcricao:
        return "invalido"

    client = get_openai_client()
    prompt_sistema = """
    Você é um classificador de intenção. Analise o texto do usuário.
    Responda APENAS com uma única palavra: 'pergunta' se o usuário está fazendo uma pergunta, 
    ou 'checklist' se ele está relatando eventos do dia.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": transcricao}
            ],
            temperature=0
        )
        return response.choices[0].message.content.lower().strip()
    except Exception as e:
        logger.error(f"Erro ao determinar intenção do áudio: {e}")
        return "invalido"

def _estruturar_e_salvar_checklist(transcricao: str, file_path: str, data_checklist: str, crianca_id: str, usuario_id: str, origem: str) -> str | None:
    """Recebe uma transcrição, estrutura com LLM e salva no banco."""
    if not transcricao.strip():
        logger.warning("A transcrição resultou em um texto vazio. Abortando.")
        return None

    logger.info("Enviando para o LLM estruturar o checklist...")
    prompt_sistema = """Você é o Manolo, um assistente de desenvolvimento infantil.
Sua tarefa é ler uma transcrição de áudio enviada pelos pais e extrair as informações para um checklist diário.
Retorne APENAS um JSON válido. 
O JSON deve ter duas chaves principais: 
1. "campos_preenchidos": com os dados encontrados sobre sono, alimentação, humor, comunicação e regulação.
2. "campos_ausentes": uma lista de strings com os temas de rotina que os pais não mencionaram (ex: ["brincar", "tela", "higiene", "vestuario", "movimento"]).
"""
    
    client = get_openai_client()
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": f"Transcrição de hoje ({data_checklist}): {transcricao}"}
            ],
            temperature=0.3
        )
        analise_json = response.choices[0].message.content
        logger.info(f"Retorno estruturado do LLM:\n{analise_json}")
    except Exception as e:
        logger.error(f"Erro ao chamar LLM para estruturar checklist: {e}")
        return

    logger.info("Salvando registro de mídia no banco...")
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO midias 
                    (crianca_id, usuario_id, tipo, contexto, storage_path, transcricao, analise_agente, processado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (crianca_id, usuario_id, 'audio', 'checklist', file_path, transcricao, analise_json, True))
            conn.commit()
        
        logger.info("Estruturando informações nas tabelas de checklist...")
        salvar_checklist(crianca_id, usuario_id, data_checklist, origem, analise_json)
        
        logger.info("Atualizando perfil vivo com base no novo checklist...")
        atualizar_perfil(crianca_id)
        # TODO: Retornar um JSON que indique sucesso e os campos ausentes para a notificação.

        return analise_json
        
    except Exception as e:
        logger.error(f"Erro ao salvar no banco: {e}")
        return None

def _processar_arquivo_audio(file_path: str, data_checklist: str, crianca_id: str, usuario_id: str, origem: str) -> str | None:
    """
    Função completa que transcreve e depois chama a estruturação.
    Usada principalmente pela CLI para manter a compatibilidade.
    Retorna o JSON da análise em caso de sucesso, ou None em caso de falha.
    """
    if not os.path.exists(file_path):
        logger.error(f"Arquivo de áudio não encontrado: {file_path}")
        return None

    logger.info(f"Transcrevendo áudio via API da OpenAI: {file_path} ...")
    client = get_openai_client()
    try:
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="pt"
            )
        transcricao = transcript.text.strip()
        logger.info(f"Transcrição concluída: '{transcricao}'")
    except Exception as e:
        logger.error(f"Erro ao chamar a API de transcrição do Whisper: {e}")
        return None

    return _estruturar_e_salvar_checklist(transcricao, file_path, data_checklist, crianca_id, usuario_id, origem)

def main():
    """Função para executar a ingestão via linha de comando."""
    parser = argparse.ArgumentParser(description="Transcreve áudio com Whisper e estrutura checklist via LLM.")
    parser.add_argument("--file", required=True, help="Caminho para o arquivo de áudio")
    parser.add_argument("--data", required=True, help="Data do checklist (YYYY-MM-DD)")
    args = parser.parse_args()

    # Para execução via CLI, precisamos de um usuário. Usaremos um UUID de teste.
    usuario_id_cli = 'b0000000-0000-0000-0000-000000000001'

    # Mantém a compatibilidade com a execução via CLI usando os IDs hardcoded
    _processar_arquivo_audio(args.file, args.data, CRIANCA_ID, usuario_id_cli, 'terminal')

if __name__ == "__main__":
    main()