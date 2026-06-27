"""Módulo principal do FastAPI e webhook WhatsApp."""

import logging
from datetime import datetime
from fastapi import FastAPI, Request, Response, HTTPException, BackgroundTasks

from core.database import get_connection
from channels.whatsapp import enviar_mensagem, baixar_e_salvar_midia, enviar_mensagem_async
from agent.agent import perguntar_ao_manolo
from core.config import settings
from ingestion.ingestion_audio import _determinar_intencao_audio, _estruturar_e_salvar_checklist
import tempfile, os, json, asyncio

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from core.clients import get_openai_client

app = FastAPI(title="Manolo API", description="Webhook para WhatsApp")

def verificar_acesso(telefone: str):
    """Busca o usuário no banco pelo telefone."""
    try:
        telefone = telefone.replace("+", "")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, nome, perfil FROM usuarios WHERE telefone_whatsapp = %s AND ativo = TRUE", (telefone,))
                usuario_data = cur.fetchone()
                if usuario_data:
                    # Retorna um dicionário para facilitar o acesso
                    return {"id": usuario_data[0], "nome": usuario_data[1], "perfil": usuario_data[2]}
    except Exception as e:
        logger.error(f"Erro ao verificar usuário: {e}")
    return None

async def processar_e_enviar_resposta(pergunta: str, telefone_remetente: str, nome_usuario: str, perfil_usuario: str):
    """Processa a pergunta em background e envia a resposta ao usuário."""
    try:
        logger.info(f"Processando pergunta para {nome_usuario} em background: '{pergunta}'")
        resposta = await asyncio.to_thread(
            perguntar_ao_manolo,
            pergunta=pergunta,
            crianca_id=settings.CRIANCA_ID_PILOTO,
            telefone_whatsapp=telefone_remetente,
            nome_usuario=nome_usuario,
            perfil_usuario=perfil_usuario
        )
        await enviar_mensagem_async(resposta, telefone_remetente)
    except Exception as e:
        logger.error(f"Falha ao processar e enviar resposta em background: {e}", exc_info=True)
        await enviar_mensagem_async(
            "🤖 Ops! Algo deu errado ao processar sua pergunta. A equipe já foi notificada.",
            telefone_remetente
        )

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
        if not entry: return Response(status_code=200)
        
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
            background_tasks.add_task(enviar_mensagem_async, "Desculpe, este número não está autorizado a interagir com o Manolo.", telefone_remetente)
            return Response(status_code=200)

        usuario_id, nome_usuario, perfil_usuario = usuario['id'], usuario['nome'], usuario['perfil']
        tipo = mensagem.get("type")
        
        if tipo == "text":
            texto = mensagem.get("text", {}).get("body", "")
            if not texto: return Response(status_code=200)
            
            logger.info(f"Mensagem de texto recebida de {nome_usuario}: {texto}")
            background_tasks.add_task(enviar_mensagem_async, "Consultando...", telefone_remetente)
            background_tasks.add_task(processar_e_enviar_resposta, texto, telefone_remetente, nome_usuario, perfil_usuario)
        
        elif tipo == "audio":
            media_id = mensagem.get("audio", {}).get("id")
            if not media_id: return Response(status_code=200)

            logger.info(f"Áudio recebido de {nome_usuario}. Media ID: {media_id}")
            background_tasks.add_task(enviar_mensagem_async, "Recebi seu áudio! Vou processá-lo e te aviso em instantes.", telefone_remetente)
            background_tasks.add_task(processar_audio, media_id, usuario_id, telefone_remetente, nome_usuario, perfil_usuario)

    except Exception as e:
        logger.error(f"Erro crítico no processamento do webhook: {e}", exc_info=True)
    
    return Response(status_code=200)

async def processar_audio(media_id: str, uid: str, telefone: str, nome: str, perfil: str):
    audio_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".oga") as temp_audio:
            audio_path = temp_audio.name
        await baixar_e_salvar_midia(media_id, audio_path)
        
        client = get_openai_client()
        transcript = await asyncio.to_thread(client.audio.transcriptions.create, model="whisper-1", file=open(audio_path, "rb"), language="pt")
        transcricao = transcript.text.strip()
        logger.info(f"Transcrição do áudio: '{transcricao}'")

        if not transcricao:
            await enviar_mensagem_async("Não consegui entender o que foi dito no áudio.", telefone)
            return

        intencao = _determinar_intencao_audio(transcricao)
        logger.info(f"Intenção do áudio detectada como: '{intencao}'")
        
        if intencao == 'pergunta':
            await processar_e_enviar_resposta(transcricao, telefone, nome, perfil)
        
        elif intencao == 'checklist':
            analise_json_str = await asyncio.to_thread(_estruturar_e_salvar_checklist, transcricao, audio_path, datetime.now().strftime('%Y-%m-%d'), settings.CRIANCA_ID_PILOTO, uid, 'whatsapp_audio')
            if analise_json_str:
                dados = json.loads(analise_json_str)
                campos_ausentes = dados.get("campos_ausentes", [])
                resposta = "Checklist de hoje salvo com sucesso! ✅"
                if campos_ausentes:
                    resposta += f"\n\nNotei que você não mencionou: {', '.join(campos_ausentes)}. Gostaria de adicionar algo sobre isso?"
                await enviar_mensagem_async(resposta, telefone)
            else:
                raise ValueError("Falha ao processar o áudio como checklist.")
        else:
            await enviar_mensagem_async("Não tenho certeza se isso foi uma pergunta ou um checklist. Pode tentar de novo?", telefone)

    except Exception as e:
        logger.error(f"Falha na tarefa de background (processar_audio): {e}", exc_info=True)
        await enviar_mensagem_async("🤖 Ops! Algo deu errado ao processar seu áudio. A equipe técnica já foi notificada.", telefone)
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
