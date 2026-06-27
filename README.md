# Manolo — Assistente de Acompanhamento Infantil

O Manolo é um sistema pessoal de acompanhamento do desenvolvimento infantil, projetado para centralizar o histórico de uma criança e permitir que um agente de IA forneça insights contextuais.

Este documento fornece as instruções para configurar e executar o ambiente de desenvolvimento localmente usando Docker.

## Pré-requisitos

- [Docker](https://www.docker.com/products/docker-desktop/)
- [Docker Compose](https://docs.docker.com/compose/install/) (geralmente incluído no Docker Desktop)

## 1. Configuração do Ambiente

### 1.1. Arquivo de Ambiente (.env)

Crie um arquivo chamado `.env` na raiz do projeto. Ele guardará suas chaves de API e configurações. Comece com o seguinte conteúdo:

```env
# Chaves de API
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Configuração do Banco de Dados (usado pelo docker-compose)
POSTGRES_DB=manolo
POSTGRES_USER=manolo
POSTGRES_PASSWORD=manolo

# URL de conexão para os scripts Python
DATABASE_URL=postgresql://manolo:manolo@db:5432/manolo

# Configuração do WhatsApp (Fase 3)
WHATSAPP_TOKEN=
WHATSAPP_VERIFY_TOKEN=manolo_secreto_123
WHATSAPP_PHONE_ID=

# Configuração do Telegram (Teste)
TELEGRAM_BOT_TOKEN=
```
**Importante:** A `DATABASE_URL` usa `db` como hostname, que é o nome do serviço do banco de dados no `docker-compose.yml`.

### 1.2. Subir os Contêineres

Com o Docker em execução, execute o seguinte comando no terminal, na raiz do projeto:

**Na primeira vez ou após mudar `requirements.txt` ou `Dockerfile`:**
```bash
docker-compose up -d --build
```

Este comando irá:
1.  **Construir (`--build`)** a imagem Docker da sua aplicação (`app`), instalando Python, Tesseract, Poppler e as dependências do `requirements.txt`.
2.  **Iniciar (`up`)** os três serviços em background (`-d`):
    - `app`: O contêiner com o seu código Python.
    - `db`: O banco de dados PostgreSQL com a extensão pgvector.
    - `adminer`: Uma interface web para gerenciar o banco, acessível em `http://localhost:8080`.

### 1.3. Preparar o Banco de Dados

Na primeira vez que você rodar o projeto, precisará criar as tabelas e popular com os dados iniciais.

1.  **Criar as tabelas:** Execute o script `schema.sql` (ou cole o SQL de `MANOLO.md`) no Adminer (`http://localhost:8080`) ou via linha de comando.

2.  **Popular com dados iniciais (`seed.sql`):**
    ```bash
    cat seed.sql | docker-compose exec -T db psql -U manolo -d manolo
    ```

## 2. Comandos de Uso

Todos os scripts Python devem ser executados **dentro do contêiner `app`** para garantir que todas as dependências (incluindo Tesseract/Poppler) estejam disponíveis.

### Ingestão de PDF (com OCR)

Coloque o arquivo PDF na pasta do projeto e execute:
```bash
docker-compose exec app python ingestion_pdf.py --file "file_teste.pdf" --tipo laudo --especialidade fono --titulo "Avaliação Fono" --data 2026-06-19
```

### Conversar com o Agente (via Terminal)

```bash
docker-compose exec app python chat.py
```

### Teste com Telegram Bot

Adicione seu `TELEGRAM_BOT_TOKEN` no `.env` e inicie o bot:
```bash
docker-compose exec app python telegram_bot.py
```

### Teste com WhatsApp (Local)

1.  Adicione `WHATSAPP_TOKEN` e `WHATSAPP_PHONE_ID` ao `.env`.
2.  Inicie um túnel (como Ngrok ou Pinggy) para a porta 8000. Ex: `pinggy http 8000`.
3.  Configure a URL do túnel como webhook no painel da Meta for Developers.
4.  Inicie o servidor FastAPI dentro do contêiner:
    ```bash
    docker-compose exec app uvicorn main:app --host 0.0.0.0 --port 8000
    ```

## 3. Gerenciando o Ambiente Docker

### Seus dados estão salvos?

**Sim.** Graças à configuração de volumes no `docker-compose.yml`, todos os dados do banco de dados são persistidos em um volume gerenciado pelo Docker no seu computador. Você pode parar, remover e recriar os contêineres sem perder os dados.

### Comandos Úteis

- **Parar os contêineres (sem remover):**
  ```bash
  docker-compose stop
  ```

- **Parar e remover os contêineres (mantém os dados):**
  ```bash
  docker-compose down
  ```

- **DESTRUIR TUDO (remover contêineres E apagar todos os dados do banco):**
  Use este comando se quiser começar do zero, como se fosse a primeira vez.
  ```bash
  docker-compose down -v
  ```

---