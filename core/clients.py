"""Módulo para centralizar a criação de clientes de serviços externos (OpenAI, etc)."""

from openai import OpenAI

from core.config import settings

# Cria uma única instância do cliente para ser reutilizada em toda a aplicação.
# O cache de módulo do Python garante que isso seja executado apenas uma vez.
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

def get_openai_client() -> OpenAI:
    """Retorna a instância compartilhada do cliente OpenAI."""
    return openai_client