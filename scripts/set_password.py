import os
import sys
import argparse

# Adicionar raiz do projeto ao PYTHONPATH para permitir imports do core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_connection
from core.security import get_password_hash

def main():
    parser = argparse.ArgumentParser(description="Atualiza a senha e email_web de um usuário no banco de dados.")
    parser.add_argument("--usuario_id", required=True, help="ID do usuário")
    parser.add_argument("--email_web", required=True, help="Email para login web")
    parser.add_argument("--senha", required=True, help="Senha em texto plano")
    
    args = parser.parse_args()
    
    senha_hash = get_password_hash(args.senha)
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Verifica se usuário existe
                cur.execute("SELECT id, nome FROM usuarios WHERE id = %s", (args.usuario_id,))
                user = cur.fetchone()
                
                if not user:
                    print(f"Erro: Usuário com ID {args.usuario_id} não encontrado.")
                    return
                
                # Atualiza credenciais
                cur.execute("""
                    UPDATE usuarios 
                    SET email_web = %s, senha_hash = %s 
                    WHERE id = %s
                """, (args.email_web, senha_hash, args.usuario_id))
                
            conn.commit()
            print(f"Sucesso! Credenciais atualizadas para o usuário: {user['nome']} ({args.email_web})")
            
    except Exception as e:
        print(f"Erro ao acessar banco de dados: {e}")

if __name__ == "__main__":
    main()
