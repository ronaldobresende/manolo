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


async def processar_mensagem_texto(texto: str, telefone_remetente: str, nome_usuario: str, perfil_usuario: str):
    """
    Processa a mensagem de texto, mantendo o indicador 'digitando' ativo.
    """
    # Tarefa para manter o indicador "digitando" ativo
    async def manter_typing_ativo():
        while True:
            try:
                await enviar_typing(telefone_remetente, typing_on=True)
                # A API do WhatsApp recomenda enviar a cada poucos segundos.
                await asyncio.sleep(4)
            except asyncio.CancelledError:
                # Silenciosamente para quando a tarefa é cancelada
                break
            except Exception as e:
                logger.error(f"Erro ao manter 'digitando' ativo: {e}")
                break

    typing_task = asyncio.create_task(manter_typing_ativo())

    try:
        # Executa a função síncrona do agente em um thread separado
        resposta = await asyncio.to_thread(
            perguntar_ao_manolo,
            pergunta=texto,
            crianca_id=settings.CRIANCA_ID_PILOTO,
            telefone_whatsapp=telefone_remetente,
            nome_usuario=nome_usuario,
            perfil_usuario=perfil_usuario
        )

    except Exception as e:
        logger.error(f"Erro ao processar pergunta do Manolo: {e}", exc_info=True)
        resposta = "Desculpe, não consegui processar sua pergunta. A equipe já foi notificada."

    finally:
        # Cancela a tarefa de "digitando"
        typing_task.cancel()
        # Espera o cancelamento ser processado
        try:
            await typing_task
        except asyncio.CancelledError:
            pass

        # Garante que o "digitando" seja desativado
        await enviar_typing(telefone_remetente, typing_on=False)
        # Envia a resposta final
        await enviar_mensagem_async(resposta, telefone_remetente)


@app.post("/webhook")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    """Rota POST que recebe as mensagens enviadas pelos usuários via WhatsApp."""
    try:
        body = await request.json()
    except Exception:
        # Se o corpo não for JSON válido, não podemos fazer nada.
        logger.warning("Requisição recebida com corpo não-JSON.")
        return Response(status_code=400)

    try:
        # A estrutura de dados do webhook da Meta é bem aninhada.
        entry = body.get("entry", [])
        if not entry: return Response(status_code=200)

        changes = entry[0].get("changes", [])
        if not changes: return Response(status_code=200)

        value = changes[0].get("value", {})
        messages = value.get("messages", [])

        if not messages:
            # Pode ser uma notificação de status, que ignoramos por enquanto.
            return Response(status_code=200)

        mensagem = messages[0]
        telefone_remetente = mensagem.get("from")

        if not telefone_remetente:
             logger.warning("Mensagem recebida sem remetente ('from').")
             return Response(status_code=200) # Retorna 200 para não receber de novo

        usuario_tuple = verificar_acesso(telefone_remetente)
        if not usuario_tuple:
            logger.warning(f"Acesso negado para o telefone: {telefone_remetente}")
            # Usar background task para não atrasar a resposta 200 OK para a Meta
            background_tasks.add_task(
                enviar_mensagem_async,
                "Desculpe, este número não está autorizado a interagir com o Manolo.", 
                telefone_remetente
            )
            return Response(status_code=200)

        # O cursor retorna uma tupla, desempacotar para clareza.
        usuario_id, nome_usuario, perfil_usuario = usuario_tuple

        tipo = mensagem.get("type")

        if tipo == "text":
            texto = mensagem.get("text", {}).get("body", "")
            if not texto: return Response(status_code=200)

            logger.info(f"Mensagem de texto recebida de {nome_usuario}: {texto}")

            # Adiciona a tarefa de processamento em background
            background_tasks.add_task(
                processar_mensagem_texto,
                texto=texto,
                telefone_remetente=telefone_remetente,
                nome_usuario=nome_usuario,
                perfil_usuario=perfil_usuario
            )

        elif tipo == "audio":
            media_id = mensagem.get("audio", {}).get("id")
            if not media_id: return Response(status_code=200)

            logger.info(f"Áudio recebido de {nome_usuario}. Media ID: {media_id}")
            # Envia uma confirmação imediata
            background_tasks.add_task(
                enviar_mensagem_async,
                "Recebi seu áudio! Vou processá-lo e te aviso em instantes.", 
                telefone_remetente
            )

            # Envolve a tarefa de background em uma função para capturar exceções
            async def processar_e_notificar(uid: str, telefone: str, nome: str, perfil: str):
                audio_path = None
                try:
                    # 1. Criar arquivo temporário e baixar
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".oga") as temp_audio:
                        audio_path = temp_audio.name
                    await baixar_e_salvar_midia(media_id, audio_path)
                    logger.info(f"Mídia baixada para o caminho temporário: {audio_path}")

                    # 2. Transcrever o áudio
                    client = get_openai_client()
                    transcript = await asyncio.to_thread(
                        client.audio.transcriptions.create,
                        model="whisper-1", file=open(audio_path, "rb"), language="pt"
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
                        # Reutiliza a mesma lógica da mensagem de texto
                        await processar_mensagem_texto(
                            texto=transcricao,
                            telefone_remetente=telefone,
                            nome_usuario=nome,
                            perfil_usuario=perfil
                        )

                    elif intencao == 'checklist':
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
                    # Mensagem de erro amigável para o usuário
                    error_message = (
                        "🤖 Ops! Algo deu errado ao processar seu áudio.\n"
                        "Não se preocupe, a equipe técnica já foi notificada e está investigando. "
                        "Por favor, tente novamente mais tarde."
                    )
                    await enviar_mensagem_async(error_message, telefone)

                finally:
                    # Limpeza do arquivo temporário
                    if audio_path and os.path.exists(audio_path):
                        os.remove(audio_path)

            # Adiciona a tarefa de processamento de áudio ao background
            background_tasks.add_task(processar_e_notificar, usuario_id, telefone_remetente, nome_usuario, perfil_usuario)

    except Exception as e:
        logger.error(f"Erro crítico no processamento do webhook: {e}", exc_info=True)
        # Retorna 200 OK para evitar que a Meta reenvie a notificação com falha.
        # O erro já foi logado para depuração.

    return Response(status_code=200)
