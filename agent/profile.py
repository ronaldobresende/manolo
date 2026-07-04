"""Atualização do perfil vivo da criança."""

import json
import logging
from langsmith import traceable
from core.database import get_connection
from core.memory import obter_perfil_vivo, buscar_contexto_checklists # Assuming memory.py is in the root
from core.clients import get_openai_client # Assuming clients.py is in the root
from core.config import settings # Assuming config.py is in the root

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def buscar_documentos_recentes(crianca_id: str, limite_dias: int = 90) -> str:
    """Busca o conteúdo dos documentos processados recentemente para compor o contexto."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT d.titulo, d.data_documento, d.tipo, d.especialidade,
                           string_agg(c.conteudo, '\n') as texto
                    FROM documentos d
                    JOIN documento_chunks c ON d.id = c.documento_id
                    WHERE d.crianca_id = %s
                      AND d.criado_em >= NOW() - INTERVAL '1 day' * %s
                    GROUP BY d.id
                """, (crianca_id, limite_dias))
                resultados = cur.fetchall()
                
        if not resultados:
            return "Nenhum documento indexado nos últimos 90 dias."
            
        contexto = ""
        for row in resultados:
            contexto += f"--- Documento: {row['titulo']} (Tipo: {row['tipo']}, Especialidade: {row['especialidade']}, Data: {row['data_documento']}) ---\n"
            texto = row['texto']
            # Limita a 10.000 caracteres por documento para evitar excesso de tokens
            if len(texto) > 10000:
                texto = texto[:10000] + "... [texto truncado]"
            contexto += f"{texto}\n\n"
        return contexto
    except Exception as e:
        logger.error(f"Erro ao buscar documentos recentes: {e}")
        return ""

@traceable
def atualizar_perfil(crianca_id: str):
    """Lê os últimos dados da criança, pede para o LLM reescrever o perfil e salva no banco."""
    client = get_openai_client()
    
    logger.info(f"Iniciando atualização de perfil para a criança {crianca_id}...")
    
    perfil_atual = obter_perfil_vivo(crianca_id)
    checklists = buscar_contexto_checklists(crianca_id, limite_dias=30)
    documentos = buscar_documentos_recentes(crianca_id, limite_dias=90)
    
    prompt_sistema = """Você é o Manolo, um assistente especializado no acompanhamento do desenvolvimento infantil.
Sua tarefa é analisar os novos dados da criança (checklists recentes e novos documentos) e reescrever o seu "perfil vivo".
O perfil vivo é um resumo do estado atual da criança em diferentes domínios.

Instruções:
1. Retorne APENAS um JSON válido, sem markdown ou marcações extras.
2. O JSON deve conter EXATAMENTE as seguintes chaves de nível superior: "comunicacao", "motor", "alimentacao", "sono", "regulacao" e "resumo_geral".
3. Os valores para as 5 primeiras chaves devem ser objetos JSON SIMPLES de APENAS UM NÍVEL (flat). Os valores dentro desses objetos não podem ser outros objetos (proibido objetos aninhados). Use apenas strings, números ou arrays simples de strings.
4. SÍNTESE CLÍNICA (MUITO IMPORTANTE): O Perfil Vivo NÃO É um log de eventos. NUNCA liste datas, horários isolados ou registros brutos (ex: não escreva "dormiu às 15h no dia X, às 16h no dia Y"). Em vez disso, identifique PADRÕES, QUALIDADE, RISCOS e TENDÊNCIAS (ex: "Padrão de sono instável", "Média de 2 horas de soneca", "Dificuldade para iniciar o sono noturno").
5. O valor de "resumo_geral" deve ser uma string de texto (um parágrafo resumindo de forma humana o perfil geral atual da criança).
6. Seja específico sobre tendências (melhorou, piorou, estável) citando apenas períodos amplos (ex: "na última semana").
7. Se o dado do perfil atual não foi alterado ou invalidado, mantenha-o. Integre o novo com o antigo harmoniosamente.
8. Responda sempre em português.
"""

    prompt_usuario = f"""
--- PERFIL ATUAL ---
{perfil_atual}

--- NOVOS DADOS ---

>> Checklists (últimos 30 dias):
{checklists}

>> Documentos Novos (últimos 90 dias):
{documentos}

Por favor, gere o novo perfil atualizado.
"""

    try:
        response = client.chat.completions.create(
            model=settings.LLM_MODEL_PROFILE,
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario}
            ],
            temperature=0.3
        )
        
        novo_perfil_json = response.choices[0].message.content
        dados = json.loads(novo_perfil_json)
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO perfil_crianca 
                    (crianca_id, comunicacao, motor, alimentacao, sono, regulacao, resumo_geral, atualizado_em)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (crianca_id) DO UPDATE SET
                        comunicacao = EXCLUDED.comunicacao,
                        motor = EXCLUDED.motor,
                        alimentacao = EXCLUDED.alimentacao,
                        sono = EXCLUDED.sono,
                        regulacao = EXCLUDED.regulacao,
                        resumo_geral = EXCLUDED.resumo_geral,
                        atualizado_em = NOW()
                """, (
                    crianca_id,
                    json.dumps(dados.get("comunicacao", {}), ensure_ascii=False),
                    json.dumps(dados.get("motor", {}), ensure_ascii=False),
                    json.dumps(dados.get("alimentacao", {}), ensure_ascii=False),
                    json.dumps(dados.get("sono", {}), ensure_ascii=False),
                    json.dumps(dados.get("regulacao", {}), ensure_ascii=False),
                    dados.get("resumo_geral", "")
                ))
            conn.commit()
            
        logger.info(f"Perfil da criança {crianca_id} atualizado com sucesso!")
        return dados
    except Exception as e:
        logger.error(f"Erro ao atualizar perfil: {e}")
        return None

if __name__ == "__main__":
    # Teste isolado local
    atualizar_perfil(settings.CRIANCA_ID_PILOTO)