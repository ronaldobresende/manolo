# Projeto Manolo

Assistente de acompanhamento de desenvolvimento infantil com memória longitudinal e agente contextual.
Criança piloto: Bernardo (atraso de fala e desenvolvimento).

## Referências obrigatórias

Antes de qualquer implementação, leia:
- `MANOLO.md` — arquitetura, modelo de dados, fluxos, stack completo
- `MANOLO_STATUS.md` — o que já foi feito, decisões tomadas, próximo passo

## Stack

- Python + FastAPI
- PostgreSQL + pgvector (via Docker local)
- Supabase Storage ou Cloudflare R2 (arquivos)
- Whisper local (transcrição de áudio)
- Claude API ou Groq (LLM do agente)

## Comandos principais

```bash
# Subir banco local
docker-compose up -d

# Instalar dependências
pip install -r requirements.txt

# Criar tabelas
python database.py

# Popular dados iniciais
psql -h localhost -U manolo -d manolo -f seed.sql

# Ingerir arquivo
python ingest.py --file <caminho> --tipo <pdf|audio|video>

# Conversar com o agente
python chat.py
```

## Convenções

- Variáveis de ambiente sempre via `.env` — nunca hardcoded
- UUIDs como chave primária em todas as tabelas
- Todo acesso ao banco passa por `database.py`
- Logs em português (o projeto é familiar, não corporativo)
- Comentários no código em português

## Nunca fazer

- Commitar `.env` no git
- Expor URLs públicas de arquivos no storage
- Acessar o banco diretamente sem passar por `database.py`
- Usar `print()` para debug em produção — usar `logging`
