"""Comunicação com API da Meta / WhatsApp Business."""

import logging
import httpx
from core.config import settings

logger = logging.getLogger(__name__)

def enviar_mensagem(texto: str, telefone_destino: str):
    """Envia uma mensagem de texto via WhatsApp API."""
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_ID:
        logger.error("Credenciais do WhatsApp não configuradas no .env")
        return False
        
    url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": telefone_destino,
        "type": "text",
        "text": {
            "body": texto
        }
    }
    
    logger.info(f"Tentando enviar mensagem para {telefone_destino}: '{texto}'")
    logger.debug(f"Payload de envio: {payload}")

    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=15.0)
        response.raise_for_status()
        logger.info(f"Mensagem para {telefone_destino} enviada com sucesso via API da Meta.")
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem para {telefone_destino}: {e}")
        if isinstance(e, httpx.HTTPStatusError):
            logger.error(f"Detalhes do erro: {e.response.text}")
        return False

async def enviar_typing(telefone_destino: str):
    """Envia o status 'digitando' via WhatsApp API."""
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_ID:
        logger.error("Credenciais do WhatsApp não configuradas no .env")
        return False
        
    url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # O usuário pediu 'reaction', mas o correto para 'digitando' é 'typing'
    # que na verdade é uma ação de marcar como lido e indicar que está digitando.
    # A ação correta é 'mark_as_read' e depois a API do WhatsApp mostra o typing.
    # A API oficial mudou, agora o status é enviado com 'typing'.
    payload = {
        "messaging_product": "whatsapp",
        "to": telefone_destino,
        "type": "typing"
    }
    
    logger.info(f"Enviando status 'typing' para {telefone_destino}")
    
    async with httpx.AsyncClient() as client:
        try:
            # O timeout pode ser baixo, é uma ação rápida
            response = await client.post(url, headers=headers, json=payload, timeout=5.0)
            response.raise_for_status()
            logger.info(f"Status 'typing' para {telefone_destino} enviado com sucesso.")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"[ASYNC] Erro de status HTTP ao enviar typing: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"[ASYNC] Erro inesperado ao enviar typing: {e}")
        return False

async def enviar_mensagem_async(texto: str, telefone_destino: str):
    """Envia uma mensagem de texto de forma assíncrona via WhatsApp API."""
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_ID:
        logger.error("Credenciais do WhatsApp não configuradas no .env")
        return False
        
    url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": telefone_destino,
        "type": "text",
        "text": {
            "body": texto
        }
    }
    
    logger.info(f"[ASYNC] Tentando enviar mensagem para {telefone_destino}: '{texto}'")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=15.0)
            response.raise_for_status()
            logger.info(f"[ASYNC] Mensagem para {telefone_destino} enviada com sucesso.")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"[ASYNC] Erro de status HTTP ao enviar mensagem: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"[ASYNC] Erro inesperado ao enviar mensagem: {e}")
        return False

async def baixar_e_salvar_midia(media_id: str, save_path: str):
    """
    Baixa uma mídia do WhatsApp em duas etapas e salva no caminho especificado.

    1. Usa o media_id para obter uma URL de download temporária.
    2. Faz o download do conteúdo da URL e salva no `save_path`.
    """
    if not settings.WHATSAPP_TOKEN:
        logger.error("WHATSAPP_TOKEN não configurado.")
        raise ValueError("Token do WhatsApp não encontrado nas configurações.")

    headers = {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"}
    url_get_media_url = f"https://graph.facebook.com/v19.0/{media_id}"

    async with httpx.AsyncClient() as client:
        try:
            # Etapa 1: Obter a URL da mídia
            logger.info(f"Obtendo URL para media_id: {media_id}")
            response_url = await client.get(url_get_media_url, headers=headers, timeout=15.0)
            response_url.raise_for_status()
            media_data = response_url.json()
            media_url = media_data.get("url")

            if not media_url:
                logger.error(f"Não foi possível obter a URL da mídia do WhatsApp: {media_data}")
                raise ValueError("URL da mídia não encontrada na resposta da API.")

            # Etapa 2: Baixar o arquivo de áudio
            logger.info(f"Baixando mídia da URL: {media_url}")
            response_download = await client.get(media_url, headers=headers, timeout=30.0)
            response_download.raise_for_status()
            
            # Etapa 3: Salvar o conteúdo no arquivo
            with open(save_path, "wb") as f:
                f.write(response_download.content)
            
            logger.info(f"Mídia salva com sucesso em: {save_path}")

        except httpx.HTTPStatusError as e:
            logger.error(f"Erro de status HTTP ao interagir com a API da Meta: {e.response.status_code}")
            logger.error(f"Detalhes: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao baixar mídia do WhatsApp: {e}")
            raise