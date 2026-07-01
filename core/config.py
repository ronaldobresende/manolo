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

    # Web App — CORS e autenticação futura
    # WEB_CORS_ORIGINS: origens separadas por vírgula
    # Ex: "https://manolo-app.vercel.app,http://localhost:3000"
    WEB_CORS_ORIGINS: str = "http://localhost:3000"
    # JWT — preparado para Fase 4.1 (autenticação)
    JWT_SECRET_KEY: str = "TROCAR_EM_PRODUCAO_chave_muito_secreta_aqui"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 8

    # Cloudflare R2
    R2_ENDPOINT_URL: str | None = None
    R2_ACCESS_KEY_ID: str | None = None
    R2_SECRET_ACCESS_KEY: str | None = None
    R2_BUCKET_NAME: str | None = None
    R2_PUBLIC_URL: str | None = None

    # Constantes da aplicação (o único lugar com hardcoding)
    CRIANCA_ID_PILOTO: str = "c0000000-0000-0000-0000-000000000001"
    USUARIO_ID_PILOTO: str = "b0000000-0000-0000-0000-000000000001"

    # Configurações do modelo de embedding
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

# Instância única que será importada por toda a aplicação
settings = Settings()