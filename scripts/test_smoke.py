import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent.agent import executar_grafo
from core.config import settings

def test():
    print("--- Testando RAG (Pergunta) ---")
    resp = executar_grafo(
        mensagem="Quais foram as conquistas do Bernardo nessa semana?",
        telefone="5511999999999",
        usuario_id=settings.USUARIO_ID_PILOTO,
        nome_usuario="Ronaldo",
        perfil_usuario="família",
        crianca_id=settings.CRIANCA_ID_PILOTO
    )
    print(f"Resposta:\n{resp}\n")
    
    print("--- Testando Extração (Relato de rotina) ---")
    resp2 = executar_grafo(
        mensagem="Hoje o Bernardo acordou às 08h super bem e comeu uma maçã inteira no café. Depois na fono ele chorou um pouco.",
        telefone="5511999999999",
        usuario_id=settings.USUARIO_ID_PILOTO,
        nome_usuario="Ronaldo",
        perfil_usuario="família",
        crianca_id=settings.CRIANCA_ID_PILOTO
    )
    print(f"Resposta:\n{resp2}\n")

if __name__ == "__main__":
    test()
