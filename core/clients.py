"""Módulo para centralizar a criação de clientes de serviços externos (OpenAI, etc)."""

from openai import OpenAI
from langsmith import wrap_openai

from core.config import settings

# Cria uma única instância do cliente para ser reutilizada em toda a aplicação.
# O cliente é envelopado com wrap_openai para que todas as chamadas à API (chat, embeddings)
# sejam enviadas detalhadamente (tokens, prompts, latência) para o painel do LangSmith.
openai_client = wrap_openai(OpenAI(api_key=settings.OPENAI_API_KEY))

def get_openai_client() -> OpenAI:
    """Retorna a instância compartilhada do cliente OpenAI."""
    return openai_client