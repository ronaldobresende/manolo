"""Script para ingestão de PDFs no banco de dados com embeddings."""

import os
import argparse
import logging
from dotenv import load_dotenv
import pypdf
from PIL import Image
from pdf2image import convert_from_path
import pytesseract
from langchain_text_splitters import RecursiveCharacterTextSplitter
from database import get_connection
from profile import atualizar_perfil
from clients import get_openai_client, OpenAI

# Configuração básica de log
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

# Hardcoded para a Fase 1
# TODO: Em fases futuras, obter o ID da criança e do usuário a partir do contexto da sessão
CRIANCA_ID = 'c0000000-0000-0000-0000-000000000001'
USUARIO_ID = 'b0000000-0000-0000-0000-000000000001'

def is_document_relevant(text: str, client: OpenAI) -> bool:
    """Usa um LLM para verificar se o conteúdo do documento é relevante para o contexto do projeto."""
    if not text or len(text.strip()) < 50:
        return False

    # Pega uma amostra do texto para a verificação
    sample_text = text[:2000]

    prompt = f"""
    O texto a seguir foi extraído de um documento. O contexto é o acompanhamento do desenvolvimento de uma criança (saúde, terapia, relatórios escolares, etc.).
    O documento parece ser relevante para este contexto? Responda apenas com 'sim' ou 'não'.

    Texto:
    --- INÍCIO DO TEXTO ---
    {sample_text}
    --- FIM DO TEXTO ---
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # Modelo mais rápido e barato para classificação
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=5)
        resposta_llm = response.choices[0].message.content.lower()
        logger.info(f"Amostra enviada para relevância: '{sample_text[:200].strip()}...'. Resposta da OpenAI: '{resposta_llm}'")
        return "sim" in resposta_llm
    except Exception as e:
        logger.error(f"Erro na verificação de relevância do documento: {e}")
        return False # Em caso de erro, assume que não é relevante para segurança.

def processar_pdf(file_path: str, tipo: str, especialidade: str, titulo: str, data: str, crianca_id: str, usuario_id: str):
    """Lógica principal de ingestão, extração, embedding e salvamento de um PDF."""
    
    if not os.path.exists(file_path):
        logger.error(f"Arquivo não encontrado: {file_path}")
        return

    client = get_openai_client()

    logger.info(f"Lendo PDF: {file_path}")
    try:
        reader = pypdf.PdfReader(file_path)
        text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
        logger.info(f"Texto extraído inicialmente por pypdf (primeiros 200 chars): '{text[:200].strip()}'")
        # Verifica se o texto extraído é mínimo; se for, pode ser um PDF de imagem
        if len(text.strip()) < 100:
            logger.warning("Pouco texto extraído com pypdf. Tentando OCR...")
            text = "" # Força a passagem pelo OCR
    except Exception as e:
        logger.error(f"Erro ao ler PDF com pypdf: {e}. Tentando OCR...")
        text = ""

    if not text.strip():
        try:
            logger.info("Nenhum texto encontrado. Executando OCR com Tesseract...")
            images = convert_from_path(file_path)
            ocr_texts = [pytesseract.image_to_string(image, lang='por') for image in images]
            text = "\n".join(ocr_texts)
            logger.info(f"Texto extraído via OCR (primeiros 200 chars): '{text[:200].strip()}'")
            logger.info("OCR concluído com sucesso.")
        except Exception as ocr_error:
            logger.error(f"Erro fatal durante o OCR: {ocr_error}")
            return

    if not text.strip():
        logger.error("Nenhum texto pôde ser extraído do PDF, nem mesmo com OCR.")
        return

    logger.info("Verificando relevância do conteúdo do documento...")
    if not is_document_relevant(text, client):
        logger.error("Documento considerado irrelevante para o contexto do projeto. A ingestão foi cancelada.")
        # Opcional: podemos salvar o documento em uma pasta "rejeitados" para análise posterior.
        return
    
    # Salva o texto extraído em um arquivo .txt para conferência
    txt_path = file_path + ".txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    logger.info(f"Texto extraído salvo para conferência em: {txt_path}")

    logger.info("Dividindo texto em chunks (~500 tokens)...")
    # Usa o encoder da OpenAI (cl100k_base) para garantir divisão correta de tokens
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base",
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = splitter.split_text(text)
    logger.info(f"{len(chunks)} chunks gerados.")

    logger.info("Gerando embeddings via OpenAI...")
    try:
        response = client.embeddings.create(
            input=chunks,
            model="text-embedding-3-small"
        )
        embeddings = [data.embedding for data in response.data]
    except Exception as e:
        logger.error(f"Erro ao gerar embeddings: {e}")
        return

    logger.info("Salvando no banco de dados...")
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 1. Inserir documento na tabela documentos
                cur.execute("""
                    INSERT INTO documentos 
                    (crianca_id, usuario_id, tipo, especialidade, titulo, data_documento, storage_path, processado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (crianca_id, usuario_id, tipo, especialidade, titulo, data, file_path, True))
                documento_id = cur.fetchone()['id']
                
                # 2. Inserir chunks na tabela documento_chunks
                for chunk, emb in zip(chunks, embeddings):
                    # Transforma lista de floats no array vetorial (ex: '[0.1, 0.2, ...]')
                    emb_str = f"[{','.join(map(str, emb))}]"
                    cur.execute("""
                        INSERT INTO documento_chunks (documento_id, crianca_id, conteudo, embedding)
                        VALUES (%s, %s, %s, %s)
                    """, (documento_id, crianca_id, chunk, emb_str))
                
            conn.commit()
        logger.info(f"Documento '{titulo}' indexado com sucesso! (ID: {documento_id})")
        
        logger.info("Atualizando perfil vivo com as novas informações...")
        atualizar_perfil(crianca_id)
        
    except Exception as e:
        logger.error(f"Erro ao salvar no banco: {e}")

def main():
    """Wrapper para executar a ingestão via linha de comando."""
    parser = argparse.ArgumentParser(description="Ingere um PDF, divide em chunks e gera embeddings.")
    parser.add_argument("--file", required=True, help="Caminho para o arquivo PDF")
    parser.add_argument("--tipo", required=True, choices=['laudo', 'relatorio_sessao', 'avaliacao', 'receita', 'outro'], help="Tipo do documento")
    parser.add_argument("--especialidade", required=True, help="Especialidade (ex: fono, TO)")
    parser.add_argument("--titulo", required=True, help="Título do documento")
    parser.add_argument("--data", required=True, help="Data do documento (YYYY-MM-DD)")
    
    args = parser.parse_args()
    processar_pdf(args.file, args.tipo, args.especialidade, args.titulo, args.data, CRIANCA_ID, USUARIO_ID)

if __name__ == "__main__":
    main()