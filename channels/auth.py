import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from core.database import _query_one
from core.security import verify_password, create_access_token

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    nome: str
    perfil: str

@auth_router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    """
    Autentica usuário via email_web e senha.
    OAuth2PasswordRequestForm espera 'username' e 'password'. 
    Nós usaremos o campo 'username' para enviar o 'email_web'.
    """
    email_web = form_data.username
    password = form_data.password
    
    # Busca usuário pelo email_web
    user = _query_one("SELECT * FROM usuarios WHERE email_web = %s AND ativo = TRUE", (email_web,))
    
    if not user:
        # Para evitar user enumeration timing attacks, idealmente deveríamos dar um hash falso,
        # mas para MVP retornamos erro simples.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Verifica a senha
    senha_hash = user.get("senha_hash")
    if not senha_hash or not verify_password(password, senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Cria token JWT
    access_token = create_access_token(
        data={"sub": str(user["id"]), "perfil": user["perfil"]}
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user_id": str(user["id"]),
        "nome": user["nome"],
        "perfil": user["perfil"]
    }
