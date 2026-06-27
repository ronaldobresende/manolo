"""Estruturação e preenchimento do checklist diário."""

import logging
import json
from core.database import get_connection

logger = logging.getLogger(__name__)

def salvar_checklist(crianca_id: str, usuario_id: str, data: str, origem: str, analise_json: str):
    """
    Lê o JSON estruturado pelo LLM e persiste nas tabelas relacionais.
    """
    try:
        dados = json.loads(analise_json)
        campos = dados.get("campos_preenchidos", {})
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 1. Tabela raiz: checklists (Cria ou atualiza para a data)
                cur.execute("""
                    INSERT INTO checklists (crianca_id, usuario_id, data, origem)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (crianca_id, data) DO UPDATE 
                    SET origem = EXCLUDED.origem
                    RETURNING id
                """, (crianca_id, usuario_id, data, origem))
                checklist_id = cur.fetchone()['id']
                
                # 2. Distribuição Best-Effort (Fase 1)
                
                # Sono
                if "sono" in campos:
                    notas_sono = json.dumps(campos["sono"], ensure_ascii=False)
                    cur.execute("""
                        INSERT INTO checklist_sono (checklist_id, notas)
                        VALUES (%s, %s)
                        ON CONFLICT (checklist_id) DO UPDATE SET notas = EXCLUDED.notas
                    """, (checklist_id, notas_sono))

                # Humor e Regulação
                if "humor" in campos or "regulação" in campos:
                    teve_crise = "chorou" in json.dumps(campos).lower() or "crise" in json.dumps(campos).lower()
                    notas_humor = f"Humor: {campos.get('humor', {})} | Regulação: {campos.get('regulação', {})}"
                    cur.execute("""
                        INSERT INTO checklist_humor (checklist_id, teve_crise, notas)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (checklist_id) DO UPDATE 
                        SET teve_crise = EXCLUDED.teve_crise, notas = EXCLUDED.notas
                    """, (checklist_id, teve_crise, notas_humor))

                # Observações Livres / Alimentação detalhada / Etc
                diferente_hoje = "Detalhes estruturados extraídos do áudio:\n"
                for chave, valor in campos.items():
                    diferente_hoje += f"- {chave.upper()}: {valor}\n"

                cur.execute("""
                    INSERT INTO checklist_observacoes (checklist_id, diferente_hoje)
                    VALUES (%s, %s)
                    ON CONFLICT (checklist_id) DO UPDATE SET diferente_hoje = EXCLUDED.diferente_hoje
                """, (checklist_id, diferente_hoje))

            conn.commit()
        logger.info(f"Checklist salvo com sucesso nas tabelas relacionais! (Checklist ID: {checklist_id})")
        return checklist_id
    except Exception as e:
        logger.error(f"Erro ao salvar checklist: {e}")
        return None