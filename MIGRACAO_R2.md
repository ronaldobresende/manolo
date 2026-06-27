# Plano de Migração: Armazenamento Local para Cloudflare R2

> **Objetivo:** Substituir o armazenamento de arquivos no sistema de arquivos local (dentro do contêiner Docker) pelo Cloudflare R2, que é compatível com a API S3. Isso garantirá a persistência, segurança e escalabilidade dos arquivos de mídia (áudios) e documentos (PDFs).

---

## Visão Geral

Atualmente, os arquivos de mídia (áudio, PDF) são baixados para um diretório temporário no contêiner, processados, e o caminho local (`/tmp/...`) é salvo na coluna `storage_path` das tabelas `midias` e `documentos`. Após o processamento, o arquivo temporário é removido, o que significa que o arquivo original não está sendo persistido em lugar nenhum.

A migração seguirá os seguintes passos:

1.  **Configuração:** Adicionar as credenciais do Cloudflare R2 ao ambiente e instalar a dependência `boto3`.
2.  **Cliente de Storage:** Criar um módulo centralizado para interagir com o R2 (upload, geração de URL, etc.).
3.  **Refatoração da Ingestão:** Modificar os scripts de ingestão (`ingestion_audio.py` e `ingestion_pdf.py`) para, após o processamento, fazer o upload do arquivo para o R2 e salvar a URL/chave do objeto no banco de dados, em vez do caminho local.
4.  **Validação:** Testar o fluxo de ponta a ponta para garantir que os arquivos estão sendo salvos no R2 e que as referências no banco de dados estão corretas.

---

## Passo a Passo

### 1. Configuração e Dependências

-   **Arquivo `.env`**: Adicionar as novas variáveis de ambiente para o Cloudflare R2. O endpoint é crucial para o `boto3` se conectar ao R2 em vez da AWS.

    ```env
    # ... outras variáveis

    # Cloudflare R2 / S3
    R2_ENDPOINT_URL=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
    R2_ACCESS_KEY_ID=<SUA_ACCESS_KEY>
    R2_SECRET_ACCESS_KEY=<SUA_SECRET_KEY>
    R2_BUCKET_NAME=manolo
    ```

-   **Arquivo `requirements.txt`**: Adicionar a biblioteca `boto3`, que é o SDK da AWS para Python e funciona com qualquer serviço compatível com S3.

    ```txt
    # ... outras dependências
    boto3
    ```

-   **Arquivo `core/config.py`**: Atualizar a classe `Settings` para carregar as novas variáveis de ambiente.

    ```python
    class Settings(BaseSettings):
        # ...
        R2_ENDPOINT_URL: str
        R2_ACCESS_KEY_ID: str
        R2_SECRET_ACCESS_KEY: str
        R2_BUCKET_NAME: str
        # ...
    ```

### 2. Criação do Cliente de Storage

-   **Novo arquivo `core/storage.py`**: Criar um novo módulo para encapsular a lógica de interação com o R2.

    ```python
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
            public_url = f"{settings.R2_ENDPOINT_URL}/{settings.R2_BUCKET_NAME}/{object_name}"
            logger.info(f"Arquivo {file_path} enviado para {public_url}")
            return public_url
        except ClientError as e:
            logger.error(f"Erro ao fazer upload para o R2: {e}")
            return None
    ```

### 3. Refatoração dos Módulos de Ingestão

O ponto central da mudança é nos scripts que hoje salvam o caminho do arquivo no banco.

-   **Modificar `ingestion/ingestion_audio.py`**:

    No final da função `_estruturar_e_salvar_checklist`, antes de salvar no banco, adicionar a chamada para o upload.

    ```python
    # Em ingestion/ingestion_audio.py, dentro de _estruturar_e_salvar_checklist
    
    # ... após a análise do LLM
    from core.storage import upload_file_to_r2
    import uuid

    # 1. Fazer o upload do arquivo de áudio original para o R2
    object_name = f"audio/{crianca_id}/{uuid.uuid4()}.oga"
    storage_url = upload_file_to_r2(file_path, object_name)

    if not storage_url:
        logger.error("Falha no upload para o R2. Abortando salvamento no banco.")
        return None

    # 2. Salvar a URL do R2 no banco, em vez do caminho temporário
    # ... no INSERT INTO midias ...
    # VALUES (%s, ..., %s, ...), (..., storage_url, ...)
    ```

-   **Modificar `ingestion/pdf_processor.py` (e similares)**:

    O mesmo padrão deve ser aplicado ao processamento de PDFs. A função `processar_pdf` deve ser alterada para:
    1.  Receber o caminho do arquivo PDF temporário.
    2.  Chamar `upload_file_to_r2` para enviá-lo ao R2, gerando um `object_name` único (ex: `documentos/<crianca_id>/<uuid>.pdf`).
    3.  Salvar a `storage_url` retornada na tabela `documentos`.

### 4. Verificação e Validação

-   **Reconstruir o contêiner**: Após as alterações, é preciso reconstruir a imagem Docker para instalar o `boto3`.
    ```bash
    docker-compose up -d --build
    ```
-   **Teste de ponta a ponta**:
    1.  Enviar um áudio pelo Telegram ou WhatsApp.
    2.  Verificar no painel do Cloudflare R2 se o arquivo `.oga` apareceu no bucket.
    3.  Consultar a tabela `midias` no banco de dados (via Adminer) e confirmar que a coluna `storage_path` contém a URL completa do R2.
    4.  Verificar os logs da aplicação para garantir que não houve erros de upload e que o arquivo temporário local foi removido.
    5.  Repetir o processo para um arquivo PDF.