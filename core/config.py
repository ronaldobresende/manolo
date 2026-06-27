"""
Módulo de Configurações Centralizadas.

Carrega as variáveis de ambiente a partir do arquivo .env e define constantes
da aplicação usando Pydantic para validação.

Esta é a ÚNICA fonte de verdade para configurações em todo o projeto.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Define e valida as configurações da aplicação."""
    # Carregado do .env
    DATABASE_URL: str
    OPENAI_API_KEY: str
    TELEGRAM_TOKEN: str
    WHATSAPP_TOKEN: str | None = None
    WHATSAPP_VERIFY_TOKEN: str = "manolo_default_secret"
    WHATSAPP_PHONE_ID: str | None = None

    # Constantes da aplicação (o único lugar com hardcoding)
    CRIANCA_ID_PILOTO: str = "c0000000-0000-0000-0000-000000000001"
    USUARIO_ID_PILOTO: str = "b0000000-0000-0000-0000-000000000001"

    # Configurações do modelo de embedding
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

# Instância única que será importada por toda a aplicação
settings = Settings()