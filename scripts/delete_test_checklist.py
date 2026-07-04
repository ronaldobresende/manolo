import os
import sys
import logging

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import get_connection

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def delete_test_checklist():
    # Este foi exatamente o ID que apareceu no seu log do teste de fumaça
    checklist_id = "8a099931-357b-434a-910e-eaf33d3a1007"
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Graças às chaves estrangeiras com CASCADE do banco de dados relacional,
                # deletar da tabela principal irá limpar automaticamente das tabelas de sono, alimentação, etc.
                cur.execute("DELETE FROM checklists WHERE id = %s", (checklist_id,))
                
                if cur.rowcount > 0:
                    logger.info(f"✅ O checklist de teste ({checklist_id}) foi removido com sucesso!")
                else:
                    logger.info(f"⚠️ O checklist ({checklist_id}) não foi encontrado. Talvez já tenha sido removido.")
                    
            conn.commit()
    except Exception as e:
        logger.error(f"❌ Erro ao tentar deletar o registro: {e}")

if __name__ == "__main__":
    delete_test_checklist()
