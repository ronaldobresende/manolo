import os
import sys
import json
import logging
from typing import Optional
from pydantic import BaseModel, Field

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import get_connection
from core.clients import get_openai_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CochiloExtracao(BaseModel):
    teve_cochilo: bool = Field(description="Se a criança cochilou à tarde")
    cochilo_inicio: Optional[str] = Field(None, description="Horário de início do cochilo (HH:MM)")
    cochilo_fim: Optional[str] = Field(None, description="Horário de fim do cochilo (HH:MM)")

def run_backfill():
    client = get_openai_client()
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Buscar todos os registros de sono que não têm cochilo_inicio preenchido
            cur.execute("""
                SELECT s.checklist_id, c.data, c.resumo_dia, s.notas 
                FROM checklist_sono s
                JOIN checklists c ON c.id = s.checklist_id
                WHERE s.cochilo_inicio IS NULL AND s.cochilo_fim IS NULL
            """)
            rows = cur.fetchall()
            
            logger.info(f"Encontrados {len(rows)} registros para processar...")
            
            for row in rows:
                checklist_id = row['checklist_id'] if isinstance(row, dict) else row[0]
                data = row['data'] if isinstance(row, dict) else row[1]
                resumo = row['resumo_dia'] if isinstance(row, dict) else row[2]
                resumo = resumo or ""
                notas = row['notas'] if isinstance(row, dict) else row[3]
                notas = notas or ""
                
                texto_combinado = f"Resumo: {resumo}\nNotas do Sono: {notas}"
                
                if not texto_combinado.strip():
                    continue
                    
                prompt = f"""Você é um extrator de horários.
Leia o seguinte relato sobre o dia {data} e extraia o horário de início e fim do cochilo da tarde (se houver).
Se não houver menção, teve_cochilo = false.

Relato:
{texto_combinado}
"""
                
                try:
                    response = client.beta.chat.completions.parse(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        response_format=CochiloExtracao,
                        temperature=0
                    )
                    extracao = response.choices[0].message.parsed
                    
                    if extracao.cochilo_inicio or extracao.cochilo_fim:
                        logger.info(f"Data {data}: Cochilo extraído ({extracao.cochilo_inicio} - {extracao.cochilo_fim})")
                        
                        # Atualiza no banco
                        cur.execute("""
                            UPDATE checklist_sono 
                            SET cochilo_inicio = %s, cochilo_fim = %s
                            WHERE checklist_id = %s
                        """, (extracao.cochilo_inicio, extracao.cochilo_fim, checklist_id))
                        conn.commit()
                    else:
                        logger.debug(f"Data {data}: Sem cochilo detectado.")
                        
                except Exception as e:
                    logger.error(f"Erro ao processar data {data}: {e}")

if __name__ == "__main__":
    run_backfill()
