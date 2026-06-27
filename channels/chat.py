"""Interface iterativa de chat via terminal (Fase 1)."""

from agent.agent import perguntar_ao_manolo
from core.config import settings

def main():
    print("="*60)
    print("🤖 Manolo CLI - Assistente Longitudinal (Fase 1)")
    print("Digite 'sair' para encerrar.")
    print("="*60)
    
    while True:
        try:
            pergunta = input("\nVocê: ")
            if pergunta.lower() in ['sair', 'exit', 'quit']:
                break
            if not pergunta.strip():
                continue

            resposta = perguntar_ao_manolo(pergunta, settings.CRIANCA_ID_PILOTO, perfil_usuario="admin (Pai)")
            print(f"\nManolo: {resposta}")
            
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()