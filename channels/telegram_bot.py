"""Bot do Telegram para testes rápidos (Fase 1.5)."""

import os
import logging
import tempfile
import json
from datetime import datetime
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from agent.agent import perguntar_ao_manolo
from core.database import get_connection
from ingestion.audio_processor import processar_midia_checklist
from ingestion.pdf_processor import processar_pdf
from core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Estados para o ConversationHandler de PDF
RECEBENDO_TITULO, RECEBENDO_TIPO, RECEBENDO_ESPECIALIDADE, RECEBENDO_DATA = range(4)

def obter_usuario_por_telegram_id(telegram_id: int):
    """Busca o usuário no banco pelo ID do Telegram."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Assumindo que teremos uma coluna 'telegram_id' na tabela 'usuarios'
                # Por enquanto, vamos retornar o usuário padrão para testes.
                cur.execute("SELECT id, nome, perfil FROM usuarios WHERE id = %s", (settings.USUARIO_ID_PILOTO,))
                return cur.fetchone()
    except Exception as e:
        logger.error(f"Erro ao verificar usuário do Telegram: {e}")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde ao comando /start"""
    await update.message.reply_text("Olá! Eu sou o Manolo. 🤖\nComo posso ajudar com o Bernardo hoje?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe mensagens de texto e manda para o agente."""
    usuario_id_telegram = update.message.from_user.id
    usuario_db = obter_usuario_por_telegram_id(usuario_id_telegram)

    if not usuario_db:
        await update.message.reply_text("Desculpe, seu usuário do Telegram não está autorizado.")
        return

    pergunta = update.message.text
    logger.info(f"Mensagem recebida: {pergunta}")

    await update.message.reply_text("Deixa eu pensar... 🤔")
    try:
        perfil_contexto = f"{usuario_db['perfil']} ({usuario_db['nome']})"
        resposta = perguntar_ao_manolo(pergunta, settings.CRIANCA_ID_PILOTO, perfil_usuario=perfil_contexto)
        await update.message.reply_text(resposta)
    except Exception as e:
        logger.error(f"Erro ao consultar o agente: {e}")
        await update.message.reply_text("Desculpe, ocorreu um erro ao tentar processar sua pergunta.")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe mensagens de áudio, processa e responde."""
    usuario_id_telegram = update.message.from_user.id
    usuario_db = obter_usuario_por_telegram_id(usuario_id_telegram)

    if not usuario_db:
        await update.message.reply_text("Desculpe, seu usuário do Telegram não está autorizado.")
        return

    await update.message.reply_text("Recebi seu áudio! 🎙️\nAnalisando e estruturando o checklist de hoje...")

    try:
        data_hoje = datetime.now().strftime("%Y-%m-%d")
        voice = await update.message.voice.get_file()

        # Executa o fluxo de ingestão em um thread separado para não bloquear o bot
        analise_json = await asyncio.to_thread(
            processar_midia_checklist,
            voice,
            voice.download_to_drive, # Passa a função de download específica do Telegram
            data_hoje,
            settings.CRIANCA_ID_PILOTO,
            usuario_db['id'],
            'telegram_audio'
        )

        if analise_json:
            dados = json.loads(analise_json)
            campos_ausentes = dados.get("campos_ausentes", [])
            resposta = "Checklist de hoje salvo com sucesso! ✅"
            if campos_ausentes:
                resposta += f"\n\nNotei que você não mencionou: {', '.join(campos_ausentes)}. Gostaria de adicionar algo sobre isso?"
            await update.message.reply_text(resposta)
        else:
            await update.message.reply_text("Não consegui processar o áudio. Pode ter ocorrido um erro na transcrição ou o modelo não está disponível. Por favor, verifique os logs.")
    except Exception as e:
        logger.error(f"Erro inesperado no handle_audio: {e}")
        await update.message.reply_text("Ocorreu um erro inesperado ao processar seu áudio. A equipe de desenvolvimento já foi notificada.")

async def handle_pdf_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo de ingestão de PDF."""
    usuario_id_telegram = update.message.from_user.id
    usuario_db = obter_usuario_por_telegram_id(usuario_id_telegram)

    if not usuario_db:
        await update.message.reply_text("Desculpe, seu usuário do Telegram não está autorizado.")
        return ConversationHandler.END

    pdf_file = update.message.document
    context.user_data['pdf_file_id'] = pdf_file.file_id
    context.user_data['pdf_original_name'] = pdf_file.file_name
    context.user_data['usuario_db_id'] = usuario_db['id']

    await update.message.reply_text(
        "Recebi um PDF! 📄\nPara arquivá-lo corretamente, preciso de algumas informações.\n\n"
        "Primeiro, qual é o **título** deste documento? (Ex: Laudo Fonoaudiológico Set/25)"
    )
    return RECEBENDO_TITULO

async def receber_titulo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe o título e pede o tipo."""
    context.user_data['titulo'] = update.message.text
    await update.message.reply_text(
        "Ótimo. Agora, qual o **tipo** do documento?\n"
        "Escolha um: `laudo`, `relatorio_sessao`, `avaliacao`, `receita` ou `outro`."
    )
    return RECEBENDO_TIPO

async def receber_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe o tipo e pede a especialidade."""
    tipo = update.message.text.lower()
    if tipo not in ['laudo', 'relatorio_sessao', 'avaliacao', 'receita', 'outro']:
        await update.message.reply_text("Tipo inválido. Por favor, escolha uma das opções: `laudo`, `relatorio_sessao`, `avaliacao`, `receita`, `outro`.")
        return RECEBENDO_TIPO
    context.user_data['tipo'] = tipo
    await update.message.reply_text("Entendido. E qual a **especialidade**? (Ex: Fono, TO, Neuropediatra)")
    return RECEBENDO_ESPECIALIDADE

async def receber_especialidade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe a especialidade e pede a data."""
    context.user_data['especialidade'] = update.message.text
    await update.message.reply_text("Quase lá! Qual a **data** do documento? (formato AAAA-MM-DD)")
    return RECEBENDO_DATA

async def receber_data_e_processar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe a data, finaliza a coleta e inicia o processamento."""
    context.user_data['data'] = update.message.text
    await update.message.reply_text("Obrigado! Recebi todas as informações. Vou iniciar o processamento do PDF. Isso pode levar um momento...")

    pdf_path = None
    try:
        # Baixar o arquivo
        pdf_file = await context.bot.get_file(context.user_data['pdf_file_id'])
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            await pdf_file.download_to_drive(temp_pdf.name)
            pdf_path = temp_pdf.name
        
        logger.info(f"PDF baixado para: {pdf_path}")

        # Executar o processamento em uma thread separada
        await asyncio.to_thread(
            processar_pdf,
            pdf_path,
            context.user_data['tipo'],
            context.user_data['especialidade'],
            context.user_data['titulo'],
            context.user_data['data'],
            settings.CRIANCA_ID_PILOTO,
            context.user_data['usuario_db_id']
        )
        
        await update.message.reply_text(f"O documento '{context.user_data['titulo']}' foi processado e arquivado com sucesso! ✅")

    except Exception as e:
        logger.error(f"Erro ao processar PDF vindo do Telegram: {e}")
        await update.message.reply_text("Ocorreu um erro ao processar o PDF. A equipe foi notificada.")
    finally:
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)
            logger.info(f"Arquivo PDF temporário removido: {pdf_path}")
        context.user_data.clear()

    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a conversa de ingestão de PDF."""
    await update.message.reply_text("Operação cancelada.")
    context.user_data.clear()
    return ConversationHandler.END

def main():
    if not settings.TELEGRAM_TOKEN:
        print("ERRO: TELEGRAM_TOKEN não encontrado no arquivo .env")
        return

    app = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    # Handler para conversas de ingestão de PDF
    pdf_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Document.PDF, handle_pdf_inicio)],
        states={
            RECEBENDO_TITULO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_titulo)],
            RECEBENDO_TIPO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_tipo)],
            RECEBENDO_ESPECIALIDADE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_especialidade)],
            RECEBENDO_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_data_e_processar)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    app.add_handler(pdf_conv_handler)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_audio))
    print("🤖 Manolo Telegram Bot rodando! Mande uma mensagem lá no Telegram. Aperte Ctrl+C no terminal para parar.")
    app.run_polling()

if __name__ == "__main__":
    main()