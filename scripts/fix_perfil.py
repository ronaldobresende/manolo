import os
import sys

# Adiciona o diretório raiz ao path para podermos importar 'agent'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.profile import atualizar_perfil
from core.config import settings

if __name__ == "__main__":
    print("Forçando regeneração do Perfil Vivo com o novo prompt clínico...")
    atualizar_perfil(settings.CRIANCA_ID_PILOTO)
    print("Concluído! Pode recarregar a página do Dashboard.")
