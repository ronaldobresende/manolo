"""Módulo principal do FastAPI e webhook WhatsApp.

Casca fina: recebe mensagens, transcreve áudio se necessário,
e delega toda a lógica de negócio ao grafo LangGraph (agent.py).
"""

import logging
import json
import tempfile
import os
import asyncio

from fastapi import FastAPI, Request, Response, HTTPException, BackgroundTasks

from core.database import get_connection
from core.config import settings
from core.clients import get_openai_client
from channels.whatsapp import enviar_mensagem_async, baixar_e_salvar_midia
from agent.agent import executar_grafo

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Manolo API", description="Webhook para WhatsApp")


# ============================================================
# AUTENTICAÇÃO
# ============================================================

def verificar_acesso(telefone: str):
    """Busca o usuário no banco pelo telefone."""
    try:
        telefone = telefone.replace("+", "")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, nome, perfil FROM usuarios WHERE telefone_whatsapp = %s AND ativo = TRUE", (telefone,))
                usuario_data = cur.fetchone()
                if usuario_data:
                    # Retorna um dicionário para facilitar o acesso (chaves de string devido ao RealDictCursor)
                    return {"id": usuario_data['id'], "nome": usuario_data['nome'], "perfil": usuario_data['perfil']}
    except Exception as e:
        logger.error(f"Erro ao verificar usuário: {e}")
    return None


# ============================================================
# PROCESSAMENTO CENTRAL (delega ao LangGraph)
# ============================================================

async def processar_e_responder(texto: str, telefone: str, usuario_id: str, nome: str, perfil: str):
    """Executa o grafo LangGraph em thread e envia a resposta."""
    try:
        logger.info(f"Processando mensagem para {nome} via LangGraph: '{texto[:80]}...'")
        resposta = await asyncio.to_thread(
            executar_grafo,
            mensagem=texto,
            telefone=telefone,
            usuario_id=str(usuario_id),
            nome_usuario=nome,
            perfil_usuario=perfil,
            crianca_id=settings.CRIANCA_ID_PILOTO,
        )
        await enviar_mensagem_async(resposta, telefone)
    except Exception as e:
        logger.error(f"Falha ao processar mensagem via LangGraph: {e}", exc_info=True)
        await enviar_mensagem_async(
            "🤖 Ops! Algo deu errado ao processar sua mensagem. A equipe já foi notificada.",
            telefone,
        )


async def processar_audio_e_responder(media_id: str, telefone: str, usuario_id: str, nome: str, perfil: str):
    """Baixa e transcreve o áudio, depois delega ao grafo."""
    audio_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".oga") as temp_audio:
            audio_path = temp_audio.name
        await baixar_e_salvar_midia(media_id, audio_path)

        client = get_openai_client()
        transcript = await asyncio.to_thread(
            client.audio.transcriptions.create,
            model="whisper-1",
            file=open(audio_path, "rb"),
            language="pt",
        )
        transcricao = transcript.text.strip()
        logger.info(f"Transcrição do áudio: '{transcricao}'")

        if not transcricao:
            await enviar_mensagem_async("Não consegui entender o que foi dito no áudio.", telefone)
            return

        # Delega ao grafo — mesma entrada que texto
        await processar_e_responder(transcricao, telefone, usuario_id, nome, perfil)

    except Exception as e:
        logger.error(f"Falha ao processar áudio: {e}", exc_info=True)
        await enviar_mensagem_async(
            "🤖 Ops! Algo deu errado ao processar seu áudio. A equipe técnica já foi notificada.",
            telefone,
        )
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)


# ============================================================
# ROTAS
# ============================================================

@app.get("/")
async def root():
    return {"message": "Manolo API está no ar! 🤖"}


@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    return {"status": "ok"}


@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token and mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verificado com sucesso pela Meta!")
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Token de verificação inválido")


@app.post("/webhook")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
    except json.JSONDecodeError:
        logger.warning("Requisição recebida com corpo não-JSON.")
        return Response(status_code=400)

    try:
        entry = body.get("entry", [])
        if not entry:
            return Response(status_code=200)

        value = entry[0].get("changes", [{}])[0].get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return Response(status_code=200)

        mensagem = messages[0]
        telefone_remetente = mensagem.get("from")

        if not telefone_remetente:
            logger.warning("Mensagem recebida sem remetente ('from').")
            return Response(status_code=200)

        usuario = verificar_acesso(telefone_remetente)
        if not usuario:
            logger.warning(f"Acesso negado para o telefone: {telefone_remetente}")
            background_tasks.add_task(
                enviar_mensagem_async,
                "Desculpe, este número não está autorizado a interagir com o Manolo.",
                telefone_remetente,
            )
            return Response(status_code=200)

        usuario_id, nome_usuario, perfil_usuario = usuario["id"], usuario["nome"], usuario["perfil"]
        tipo = mensagem.get("type")

        if tipo == "text":
            texto = mensagem.get("text", {}).get("body", "")
            if not texto:
                return Response(status_code=200)

            logger.info(f"Mensagem de texto recebida de {nome_usuario}: {texto}")
            background_tasks.add_task(enviar_mensagem_async, "Consultando...", telefone_remetente)
            background_tasks.add_task(processar_e_responder, texto, telefone_remetente, usuario_id, nome_usuario, perfil_usuario)


        elif tipo == "audio":
            media_id = mensagem.get("audio", {}).get("id")
            if not media_id:
                return Response(status_code=200)

            logger.info(f"Áudio recebido de {nome_usuario}. Media ID: {media_id}")
            background_tasks.add_task(
                enviar_mensagem_async,
                "Recebi seu áudio! Vou processá-lo e te aviso em instantes.",
                telefone_remetente,
            )
            background_tasks.add_task(processar_audio_e_responder, media_id, telefone_remetente, usuario_id, nome_usuario, perfil_usuario)

    except Exception as e:
        logger.error(f"Erro crítico no processamento do webhook: {e}", exc_info=True)

    return Response(status_code=200)
