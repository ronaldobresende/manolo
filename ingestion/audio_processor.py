"""Script para ingestão de áudios (checklists) via Whisper local e estruturação via LLM."""

import os
import argparse
import logging
from langsmith import traceable
import tempfile
from typing import Callable, Awaitable, Any
import json
import whisper
from database import get_connection
from checklist import salvar_checklist
from profile import atualizar_perfil
from clients import get_openai_client
from core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def processar_midia_checklist(
    media_object: Any,
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
        return None
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
            logger.info(f"Arquivo de mídia temporário removido: {audio_path}")

@traceable
def _processar_arquivo_audio(file_path: str, data_checklist: str, crianca_id: str, usuario_id: str, origem: str) -> str | None:
    """
    Processa um arquivo de áudio para transcrever e estruturar como checklist.
    Retorna o JSON da análise em caso de sucesso, ou None em caso de falha.
    """
    if not os.path.exists(file_path):
        logger.error(f"Arquivo de áudio não encontrado: {file_path}")
        return None

    client = get_openai_client()

    logger.info("Carregando modelo Whisper (isso pode demorar um pouco na primeira vez)...")
    try:
        model = whisper.load_model("medium")
    except Exception as e:
        logger.error(f"Erro ao carregar Whisper: {e}")
        logger.error("DICA: Você instalou o FFmpeg no sistema? O Whisper precisa dele para ler áudios.")
        return

    logger.info(f"Transcrevendo áudio: {file_path} ...")
    result = model.transcribe(file_path, language="pt")
    transcricao = result["text"].strip()
    logger.info(f"Transcrição concluída: '{transcricao}'")

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
    
    try:
        response = client.chat.completions.create(
            model=settings.LLM_MODEL_EXTRACTION_AUDIO,
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

        return analise_json
        
    except Exception as e:
        logger.error(f"Erro ao salvar no banco: {e}")
        return None

def main():
    """Função para executar a ingestão via linha de comando."""
    from manolo.core.config import settings
    parser = argparse.ArgumentParser(description="Transcreve áudio com Whisper e estrutura checklist via LLM.")
    parser.add_argument("--file", required=True, help="Caminho para o arquivo de áudio")
    parser.add_argument("--data", required=True, help="Data do checklist (YYYY-MM-DD)")
    args = parser.parse_args()

    # Mantém a compatibilidade com a execução via CLI usando os IDs hardcoded
    _processar_arquivo_audio(args.file, args.data, settings.CRIANCA_ID_PILOTO, settings.USUARIO_ID_PILOTO, 'terminal')

if __name__ == "__main__":
    main()