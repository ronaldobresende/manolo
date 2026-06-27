# Use uma imagem base oficial do Python. A versão slim é menor.
FROM python:3.11-slim

# Define variáveis de ambiente para evitar prompts interativos e garantir que os logs do Python apareçam imediatamente.
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Instala dependências do sistema necessárias para o projeto.
# - Tesseract com português (para OCR)
# - Poppler (para converter PDF em imagem para o Tesseract)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr-por \
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho
WORKDIR /app

# Copia o arquivo de dependências primeiro para aproveitar o cache de camadas do Docker
COPY requirements.txt .
# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código da aplicação para o diretório de trabalho
COPY . .

# Expõe a porta (documentação — o Render usa $PORT)
EXPOSE 8000

# Comando para iniciar a aplicação
CMD ["sh", "-c", "uvicorn channels.main:app --host 0.0.0.0 --port ${PORT:-8000}"]