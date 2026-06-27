# core/storage.py
import logging
import boto3
from botocore.exceptions import ClientError
from core.config import settings

logger = logging.getLogger(__name__)

def get_s3_client():
    """Retorna um cliente boto3 configurado para o Cloudflare R2."""
    return boto3.client(
        service_name='s3',
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name='auto', # R2 requer 'auto'
    )

def upload_file_to_r2(file_path: str, object_name: str) -> str | None:
    """
    Faz o upload de um arquivo para o bucket R2.
    Retorna a URL pública do objeto em caso de sucesso.
    """
    client = get_s3_client()
    try:
        client.upload_file(file_path, settings.R2_BUCKET_NAME, object_name)
        # NOTA: A URL pública pode variar se o bucket não for público.
        # Para R2, o padrão é <endpoint>/<bucket>/<key>
        public_url = f"{settings.R2_PUBLIC_URL}/{object_name}"
        logger.info(f"Arquivo {file_path} enviado para {public_url}")
        return public_url
    except ClientError as e:
        logger.error(f"Erro ao fazer upload para o R2: {e}")
        return None
