"""Leitura e escrita no banco de dados e histórico."""

import os
import logging
from openai import OpenAI
from core.database import get_connection

logger = logging.getLogger(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def buscar_contexto_documentos(pergunta: str, crianca_id: str, limite: int = 5) -> str:
    """Busca os chunks de documentos mais relevantes para a pergunta (Busca Semântica RAG)."""
    try:
        # 1. Transforma a pergunta do usuário em um vetor
        response = client.embeddings.create(input=pergunta, model="text-embedding-3-small")
        embedding_pergunta = response.data[0].embedding
        emb_str = f"[{','.join(map(str, embedding_pergunta))}]"
        
        # 2. Busca no banco pela distância de cosseno (<=>) usando o pgvector
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT conteudo, 
                           1 - (embedding <=> %s::vector) as similaridade
                    FROM documento_chunks
                    WHERE crianca_id = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (emb_str, crianca_id, emb_str, limite))
                
                resultados = cur.fetchall()
        
        if not resultados:
            return "Nenhum documento histórico relevante encontrado para essa pergunta."
            
        contexto = ""
        for i, row in enumerate(resultados):
            contexto += f"--- Trecho Documento {i+1} ---\n{row['conteudo']}\n\n"
        return contexto
        
    except Exception as e:
        logger.error(f"Erro na busca vetorial: {e}")
        return ""

def obter_perfil_vivo(crianca_id: str) -> str:
    """Recupera o perfil vivo atual da criança direto do banco."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM perfil_crianca WHERE crianca_id = %s", (crianca_id,))
                perfil = cur.fetchone()
                if perfil:
                    # Retorna os dados agregados para colocar no Prompt
                    return f"Comunicação: {perfil['comunicacao']}\nMotor: {perfil['motor']}\nAlimentação: {perfil['alimentacao']}\nSono: {perfil['sono']}\nRegulação: {perfil['regulacao']}\nResumo Geral: {perfil['resumo_geral']}"
    except Exception as e:
        logger.error(f"Erro ao buscar perfil vivo: {e}")
    return "Perfil não encontrado ou não inicializado."

def buscar_contexto_checklists(crianca_id: str, limite_dias: int = 7) -> str:
    """Busca os últimos checklists diários no banco relacional."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        c.data, 
                        c.origem,
                        cs.notas as sono, 
                        ch.notas as humor, 
                        co.diferente_hoje as observacoes
                    FROM checklists c
                    LEFT JOIN checklist_sono cs ON c.id = cs.checklist_id
                    LEFT JOIN checklist_humor ch ON c.id = ch.checklist_id
                    LEFT JOIN checklist_observacoes co ON c.id = co.checklist_id
                    WHERE c.crianca_id = %s
                    ORDER BY c.data DESC
                    LIMIT %s
                """, (crianca_id, limite_dias))
                resultados = cur.fetchall()
        if not resultados:
            return "Nenhum checklist recente encontrado."
        contexto = ""
        for row in resultados:
            contexto += f"--- Dia {row['data']} (Origem: {row['origem']}) ---\n"
            if row['sono']: contexto += f"Sono: {row['sono']}\n"
            if row['humor']: contexto += f"Humor/Regulação: {row['humor']}\n"
            if row['observacoes']: contexto += f"Observações: {row['observacoes']}\n\n"
        return contexto
    except Exception as e:
        logger.error(f"Erro ao buscar checklists: {e}")
        return ""