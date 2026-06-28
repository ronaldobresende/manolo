-- Habilita a extensão pgcrypto (caso não esteja habilitada no Neon)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Atualiza o usuário piloto com email e senha (123456)
UPDATE usuarios
SET 
    email_web = 'ronaldo.resende@hotmail.com',
    -- Usa o algoritmo bcrypt (bf) para gerar um hash compatível com o python-bcrypt
    senha_hash = crypt('Mn@141295', gen_salt('bf', 12))
WHERE 
    id = 'b0000000-0000-0000-0000-000000000001';

-- Verifica se a atualização foi bem sucedida
SELECT id, nome, email_web, senha_hash 
FROM usuarios 
WHERE id = 'b0000000-0000-0000-0000-000000000001';
