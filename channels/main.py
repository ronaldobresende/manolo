"""Módulo principal do FastAPI e webhook WhatsApp."""

import logging
from datetime import datetime
from fastapi import FastAPI, Request, Response, HTTPException, BackgroundTasks

from core.database import get_connection
from channels.whatsapp import enviar_mensagem, baixar_e_salvar_midia, enviar_mensagem_async, enviar_typing
from agent.agent import perguntar_ao_manolo
from core.config import settings # Importa a instância de configurações
# Importações atualizadas para o novo fluxo de áudio
from ingestion.ingestion_audio import _determinar_intencao_audio, _estruturar_e_salvar_checklist
import tempfile, os, json, asyncio, functools

# Alterado para DEBUG para logs mais detalhados
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Importação que estava faltando e causou o NameError
from core.clients import get_openai_client

app = FastAPI(title="Manolo API", description="Webhook para WhatsApp")

def verificar_acesso(telefone: str):
    """Busca o usuário no banco pelo telefone."""
    try:
        # WhatsApp manda o telefone puro (ex: 5511999999999) ou com '+' na frente.
        telefone = telefone.replace("+", "")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, nome, perfil FROM usuarios WHERE telefone_whatsapp = %s AND ativo = TRUE", (telefone,))
                return cur.fetchone()
    except Exception as e:
        logger.error(f"Erro ao verificar usuário: {e}")
    return None

@app.get("/")
async def root():
    """Rota raiz para verificar se a API está no ar."""
    return {"message": "Manolo API está no ar! 🤖"}

@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    """Rota de health check para o Render e UptimeRobot."""
    return {"status": "ok"}

@app.get("/webhook")
async def verify_webhook(request: Request):
    """Rota GET usada pela Meta para verificar o webhook na configuração do painel."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
            logger.info("Webhook verificado com sucesso pela Meta!")
            return Response(content=challenge, media_type="text/plain")
        else:
            raise HTTPException(status_code=403, detail="Token de verificação inválido")
    raise HTTPException(status_code=400, detail="Requisição inválida")

@app.post("/webhook")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    """Rota POST que recebe as mensagens enviadas pelos usuários via WhatsApp."""
    try:
        body = await request.json()
    except Exception:
        return {"status": "error", "message": "Corpo inválido"}

    try:
        entry = body.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        
        if not messages:
            return {"status": "ok", "message": "Nenhuma mensagem recebida"}
            
        mensagem = messages[0]
        telefone_remetente = mensagem.get("from")
        
        if not telefone_remetente:
             return {"status": "ok"}
             
        usuario = verificar_acesso(telefone_remetente)
        if not usuario:
            logger.warning(f"Acesso negado para o telefone: {telefone_remetente}")
            enviar_mensagem("Desculpe, este número não está autorizado a interagir com o Manolo.", telefone_remetente)
            return {"status": "ok"}

        # Correção: Acessar os valores do dicionário retornado pelo banco pelas chaves.
        usuario_id, nome_usuario, perfil_usuario = usuario['id'], usuario['nome'], usuario['perfil']

        tipo = mensagem.get("type")
        
        if tipo == "text":
            texto = mensagem.get("text", {}).get("body", "")
            logger.info(f"Mensagem de texto recebida de {nome_usuario}: {texto}")
            
            # Envia o status "digitando"
            await enviar_typing(telefone_remetente)
            
            resposta = await asyncio.to_thread(
                perguntar_ao_manolo,
                pergunta=texto, 
                crianca_id=settings.CRIANCA_ID_PILOTO, 
                telefone_whatsapp=telefone_remetente, 
                nome_usuario=nome_usuario,
                perfil_usuario=perfil_usuario
            )
            await enviar_mensagem_async(resposta, telefone_remetente)
        
        elif tipo == "audio":
            media_id = mensagem.get("audio", {}).get("id")
            logger.info(f"Áudio recebido de {nome_usuario}. Media ID: {media_id}")
            enviar_mensagem("Recebi seu áudio! Vou processá-lo e em breve o checklist estará atualizado.", telefone_remetente)

            # Define a função de download específica para o WhatsApp
            async def downloader_whatsapp(save_path: str):
                await baixar_e_salvar_midia(media_id, save_path)

            # Envolve a tarefa de background em uma função para capturar exceções
            async def processar_e_notificar(uid: str, telefone: str):
                audio_path = None
                try:
                    # 1. Criar arquivo temporário e baixar
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".oga") as temp_audio:
                        audio_path = temp_audio.name
                    await downloader_whatsapp(audio_path)
                    logger.info(f"Mídia baixada para o caminho temporário: {audio_path}")

                    # 2. Transcrever o áudio via API da OpenAI
                    client = get_openai_client()
                    # Executa a transcrição (que é I/O-bound) em um thread para não bloquear o loop de eventos.
                    transcript = await asyncio.to_thread(
                        client.audio.transcriptions.create,
                        model="whisper-1",
                        file=open(audio_path, "rb"),
                        language="pt"
                    )
                    transcricao = transcript.text.strip()
                    logger.info(f"Transcrição do áudio: '{transcricao}'")

                    if not transcricao:
                        await enviar_mensagem_async("Não consegui entender o que foi dito no áudio.", telefone)
                        return

                    # 3. Determinar a intenção
                    intencao = _determinar_intencao_audio(transcricao)
                    logger.info(f"Intenção do áudio detectada como: '{intencao}'")
                    
                    # 4. Roteamento
                    if intencao == 'pergunta':
                        await enviar_typing(telefone)
                        resposta = perguntar_ao_manolo(
                            pergunta=transcricao, 
                            crianca_id=settings.CRIANCA_ID_PILOTO, 
                            telefone_whatsapp=telefone, 
                            nome_usuario=nome_usuario,
                            perfil_usuario=perfil_usuario
                        )
                        await enviar_mensagem_async(resposta, telefone)
                    
                    elif intencao == 'checklist':
                        # Chama a função que apenas estrutura e salva, passando a transcrição já obtida.
                        # A função síncrona é executada em um thread para não bloquear o loop de eventos.
                        analise_json_str = await asyncio.to_thread(
                            _estruturar_e_salvar_checklist,
                            transcricao, audio_path, datetime.now().strftime('%Y-%m-%d'), settings.CRIANCA_ID_PILOTO, uid, 'whatsapp_audio'
                        )
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
                    logger.error(f"Falha na tarefa de background (processar_e_notificar): {e}", exc_info=True)
                    await enviar_mensagem_async(
                        "Ops, não consegui processar seu áudio. A equipe já foi notificada do problema.",
                        telefone
                    )
                finally:
                    if audio_path and os.path.exists(audio_path):
                        os.remove(audio_path)

            # Passa os valores como argumentos para a tarefa de background
            # para evitar problemas de closure/referência.
            background_tasks.add_task(processar_e_notificar, usuario_id, telefone_remetente)
    except Exception as e:
        logger.error(f"Erro ao processar webhook: {e}")
        
    return {"status": "ok"}