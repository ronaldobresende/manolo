"""Módulo para centralizar a criação de clientes de serviços externos (OpenAI, etc)."""

from openai import OpenAI

# Tenta importar wrap_openai de diferentes caminhos conforme a versão da biblioteca langsmith
try:
    from langsmith.wrappers import wrap_openai
except ImportError:
    try:
        from langsmith import wrap_openai
    except ImportError:
        # Fallback seguro para versões antigas ou ausência de suporte
        def wrap_openai(client):
            return client

from core.config import settings

# Cria uma única instância do cliente para ser reutilizada em toda a aplicação.
# O cliente é envelopado se wrap_openai estiver disponível para enviar traces detalhados.
openai_client = wrap_openai(OpenAI(api_key=settings.OPENAI_API_KEY))


def get_openai_client() -> OpenAI:
    """Retorna a instância compartilhada do cliente OpenAI."""
    return openai_client