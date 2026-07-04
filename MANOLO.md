# MANOLO — Documento Técnico de Referência

> Assistente de acompanhamento de desenvolvimento infantil com memória longitudinal e agente contextual.
> Este documento é o contexto completo do projeto. Use-o para orientar qualquer agente de código ou desenvolvedor.

---

## 1. Visão Geral

O Manolo é um sistema pessoal de acompanhamento do desenvolvimento infantil. Nasceu para centralizar o histórico clínico, terapêutico e cotidiano de uma criança com atraso de desenvolvimento e fala, permitindo que um agente de IA responda perguntas contextuais, identifique padrões ao longo do tempo e apoie a família e terapeutas no dia a dia.

### Pilares

- **Repositório de memória longitudinal** — laudos, relatórios de sessão, avaliações padronizadas, checklists diários, vídeos e áudios organizados e indexados semanticamente.
- **Agente contextual** — LLM com acesso ao histórico completo e a um perfil vivo da criança, atualizado automaticamente.
- **Checklist diário inteligente** — preenchido por voz, áudio, texto ou imagem (Visão Computacional), com o agente estruturando dados via Structured Outputs.
- **Atividades propostas** — terapeutas cadastram atividades vinculadas à criança, família executa e registra feedback.

### Projeto piloto

A primeira criança do sistema é **Bernardo**, filho do administrador. O sistema foi desenhado desde o início para suportar múltiplas crianças e múltiplas contas (reuso por terapeutas e clínicas).

---

## 2. Decisões de Arquitetura

| Decisão | Escolha | Motivo |
|---|---|---|
| Canal primário de input | WhatsApp Business API | Zero atrito para família, todos já usam |
| Canal de gestão | Web App (Next.js) | Histórico visual, gráficos, perfis de terapeuta |
| Autenticação | Número de telefone (WhatsApp) + JWT via cookies (Web) | Segurança e isolamento completo entre sessões |
| Backend | Python + FastAPI | Ecossistema LLM mais maduro em Python |
| Banco relacional | PostgreSQL + pgvector | Relacional + busca vetorial no mesmo banco |
| Object storage | Cloudflare R2 | Custo baixo, PDFs, vídeos, áudios e imagens |
| LLM Principal | OpenAI (gpt-4o / gpt-4o-mini) | Melhor qualidade de estruturação de dados (Structured Outputs) e Visão |
| Transcrição de áudio | Whisper API (OpenAI) | Mais rápida e consome menos recursos locais |
| Hospedagem | Render ou Railway | Simples, barato, CI/CD via GitHub |
| Multi-tenant | Por account_id em todas as tabelas | Isolamento completo entre famílias/clínicas |

### Fases de desenvolvimento

```
Fase 1 — Local, terminal
  ├── Docker Compose com Postgres + pgvector
  ├── Scripts de ingestão (PDF, áudio, vídeo)
  ├── Agente respondendo via terminal (chat.py)
  └── Validação com dados reais do Bernardo

Fase 2 — Nuvem, sem canal
  ├── Deploy do backend no Render/Railway
  ├── Supabase ou Neon para banco
  ├── R2 ou Supabase Storage para arquivos
  └── Agente acessível via HTTP

Fase 3 — WhatsApp
  ├── Webhook configurado na Meta for Developers
  ├── Checklist por voz/vídeo
  └── Consultas ao agente pelo WhatsApp

Fase 4 — Web App
  ├── Dashboard de evolução
  ├── Perfis de terapeuta
  └── Upload de PDFs e atividades
```

---

## 3. Stack e Dependências

### Python

```
fastapi>=0.111.0
uvicorn
pydantic>=2.0          # usar Pydantic v2 (Structured Outputs)
psycopg2-binary
pgvector
supabase
pypdf
openai                 # LLM do agente, embeddings e Whisper API
langsmith              # observabilidade e tracing de execução
langchain>=0.2         # RAG e busca semântica
langgraph>=0.1         # orquestração do agente (grafo de 4 nós)
httpx
python-dotenv
```

### Decisões de biblioteca — não substituir sem atualizar este documento

| Componente | Escolha | Motivo |
|---|---|---|
| LLM | `openai` SDK (gpt-4o por padrão) | Por enquanto OpenAI — trocar apenas o model string e a chave para migrar para Claude ou outro |
| Embeddings | `openai` text-embedding-3-small | Mais testado com pgvector + LangChain, boa qualidade em PT, independente do LLM do agente — não trocar depois sem reindexar todo o pgvector |
| Orquestração do agente | LangGraph | Fluxos condicionais: checklist vs pergunta livre vs ingestão |
| RAG / busca semântica | LangChain + pgvector | Integração direta com Postgres, sem serviço externo |
| Validação de dados | Pydantic v2 | Nativo no FastAPI e suporta Structured Outputs da OpenAI |
| Leitura de PDF | pypdf | Simples e suficiente para laudos — não usar pdfplumber ou pymupdf |
| Transcrição | Whisper API (OpenAI) | Rápido, preciso, elimina necessidade de hardware local pesado |

### Sobre LangGraph no Manolo

O agente usa um grafo simplificado e pragmático de 4 nós focais:

1. **classificar_intencao**: Analisa a mensagem do usuário e roteia condicionalmente.
2. **extrair_checklist_silencioso**: Extrai informações da rotina diária em JSON, salva com UPSERT cumulativo no banco, e responde sem cobranças proativas ("Anotado! ✅").
3. **responder_pergunta_rag**: Responde perguntas acessando o Perfil Vivo e o vetor de laudos. Usa guardrails para evitar alucinações.
4. **gerar_relatorio_checklist_node**: Puxa o resumo do banco quando o usuário pede, incluindo link direto pro Web App.

### Infraestrutura local (docker-compose.yml)

```yaml
version: "3.8"
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: manolo
      POSTGRES_USER: manolo
      POSTGRES_PASSWORD: manolo
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  adminer:
    image: adminer
    ports:
      - "8080:8080"

volumes:
  pgdata:
```

### Variáveis de ambiente (.env)

```
DATABASE_URL=postgresql://manolo:manolo@localhost:5432/manolo
OPENAI_API_KEY=          # LLM do agente + embeddings
                         # quando migrar para Claude: adicionar ANTHROPIC_API_KEY e trocar model string
STORAGE_BUCKET=
WHATSAPP_TOKEN=          # fase 3
WHATSAPP_VERIFY_TOKEN=   # fase 3
```

### Estrutura de pastas (monorepo)

Raiz do projeto: `C:/projects/python/manolo/` — sem subpasta extra.

```
manolo/
├── CLAUDE.md                  # lido automaticamente pelo Claude Code
├── MANOLO.md                  # referência técnica do projeto
├── MANOLO_STATUS.md           # diário de bordo entre sessões
├── README.md
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env                       # nunca commitar
├── .env.example               # commitar — valores em branco
├── .gitignore
│
├── core/                      # núcleo do sistema
│   ├── __init__.py
│   ├── config.py              # variáveis e configurações globais
│   ├── clients.py             # clientes OpenAI (c/ wrap_openai)
│   ├── database.py            # conexão e criação das tabelas
│   ├── memory.py              # busca semântica RAG
│   └── kb/                    # base de conhecimento (Denver ESDM, etc)
│
├── ingestion/                 # pipelines de ingestão de documentos
│   ├── __init__.py
│   ├── ingestion.py           # entry point / orquestrador
│   ├── pdf_processor.py       # extração de texto de PDF
│   ├── converte_pdf.py        # OCR para PDFs escaneados (débito técnico)
│   ├── ingestion_pdf.py       # pipeline completo PDF
│   ├── audio_processor.py     # transcrição Whisper API
│   ├── ingestion_audio.py     # pipeline completo áudio
│   └── ingestion_video.py     # pipeline completo vídeo (Gemini nativo)
│
├── agent/                     # cérebro do Manolo
│   ├── __init__.py
│   ├── agent.py               # orquestração LangGraph (4 nós)
│   ├── checklist.py           # parsing e persistência (UPSERT diário)
│   └── profile.py             # atualização do perfil vivo da criança
│
├── channels/                  # interfaces de entrada e backend
│   ├── __init__.py
│   ├── api.py                 # Backend API REST para o Web App
│   ├── main.py                # FastAPI + webhook do WhatsApp
│   ├── telegram_bot.py        # bot Telegram (descontinuado)
    ├── chat.py                # agente no terminal
│   └── whatsapp.py            # WhatsApp Business API
│
├── scripts/                   # utilitários CLI
│   └── seed.sql               # dados iniciais do Bernardo
│
└── tests/
    ├── testes_manuais/        # testes manuais existentes
    └── fixtures/
        ├── laudo_teste.pdf
        └── audio_teste.m4a
        
├── web/                       # Web App em Next.js (Fase 4)
    ├── app/                   # páginas e rotas (App Router)
    ├── components/            # componentes UI, Recharts, Tailwind
    └── middleware.ts          # roteamento protegido via JWT

---

## 4. Modelo de Dados

### 4.1 Núcleo — Identidade e Acesso

```sql
-- Contas: família, clínica ou terapeuta independente
CREATE TABLE accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nome TEXT NOT NULL,
  tipo TEXT CHECK (tipo IN ('família', 'clínica', 'terapeuta_independente')),
  criado_em TIMESTAMPTZ DEFAULT NOW()
);

-- Usuários autenticados pelo número de WhatsApp
CREATE TABLE usuarios (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID REFERENCES accounts(id),
  nome TEXT NOT NULL,
  telefone_whatsapp TEXT UNIQUE NOT NULL,
  email TEXT,
  perfil TEXT CHECK (perfil IN ('admin', 'família', 'terapeuta')),
  ativo BOOLEAN DEFAULT TRUE,
  criado_em TIMESTAMPTZ DEFAULT NOW()
);

-- Crianças acompanhadas
CREATE TABLE criancas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID REFERENCES accounts(id),
  nome TEXT NOT NULL,
  data_nascimento DATE NOT NULL,
  diagnosticos JSONB DEFAULT '[]',
  criado_em TIMESTAMPTZ DEFAULT NOW()
);

-- Relacionamento criança <-> terapeuta
CREATE TABLE criancas_terapeutas (
  crianca_id UUID REFERENCES criancas(id),
  usuario_id UUID REFERENCES usuarios(id),
  especialidade TEXT NOT NULL,
  ativo BOOLEAN DEFAULT TRUE,
  desde DATE DEFAULT CURRENT_DATE,
  PRIMARY KEY (crianca_id, usuario_id)
);
```

---

### 4.2 Histórico Clínico — Documentos

```sql
-- Documentos brutos (PDFs de laudos, relatórios, avaliações)
CREATE TABLE documentos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  crianca_id UUID REFERENCES criancas(id),
  usuario_id UUID REFERENCES usuarios(id),
  tipo TEXT CHECK (tipo IN ('laudo', 'relatorio_sessao', 'avaliacao', 'receita', 'outro')),
  especialidade TEXT,
  titulo TEXT NOT NULL,
  data_documento DATE,
  storage_path TEXT NOT NULL,
  processado BOOLEAN DEFAULT FALSE,
  criado_em TIMESTAMPTZ DEFAULT NOW()
);

-- Chunks de texto com embeddings para busca semântica
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documento_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  documento_id UUID REFERENCES documentos(id),
  crianca_id UUID REFERENCES criancas(id),
  conteudo TEXT NOT NULL,
  embedding VECTOR(1536),
  metadata JSONB DEFAULT '{}',
  criado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON documento_chunks USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON documento_chunks (crianca_id);
```

---

### 4.3 Avaliações Estruturadas (Bayley e similares)

```sql
CREATE TABLE avaliacoes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  crianca_id UUID REFERENCES criancas(id),
  tipo TEXT NOT NULL,
  data_avaliacao DATE NOT NULL,
  profissional TEXT,
  documento_id UUID REFERENCES documentos(id),
  criado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE avaliacoes_dominios (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  avaliacao_id UUID REFERENCES avaliacoes(id),
  dominio TEXT CHECK (dominio IN (
    'cognitivo', 'motor_fino', 'motor_grosso',
    'linguagem_receptiva', 'linguagem_expressiva', 'socio_emocional'
  )),
  pontuacao_bruta NUMERIC,
  pontuacao_composta NUMERIC,
  idade_equivalente_meses INTEGER,
  classificacao TEXT CHECK (classificacao IN (
    'muito_abaixo', 'abaixo', 'medio', 'acima', 'muito_acima'
  ))
);
```

---

### 4.4 Checklist Diário

```sql
-- Registro raiz do dia
CREATE TABLE checklists (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  crianca_id UUID REFERENCES criancas(id),
  usuario_id UUID REFERENCES usuarios(id),
  data DATE NOT NULL,
  resumo_dia TEXT CHECK (resumo_dia IN ('muito_bom', 'bom', 'regular', 'difícil')),
  origem TEXT CHECK (origem IN (
    'whatsapp_audio', 'whatsapp_video', 'whatsapp_texto', 'web', 'terminal'
  )),
  criado_em TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (crianca_id, data)
);

-- Sono
CREATE TABLE checklist_sono (
  checklist_id UUID PRIMARY KEY REFERENCES checklists(id),
  dormiu_as TIME,
  acordou_as TIME,
  acordou_noite BOOLEAN,
  cochilo BOOLEAN,
  notas TEXT
);

-- Tela
CREATE TABLE checklist_tela (
  checklist_id UUID PRIMARY KEY REFERENCES checklists(id),
  usou_tela BOOLEAN,
  tempo_minutos INTEGER,
  conteudo TEXT,
  reacao_retirada TEXT CHECK (reacao_retirada IN ('tranquilo', 'resistencia', 'crise'))
);

-- Alimentação
CREATE TABLE checklist_alimentacao (
  checklist_id UUID PRIMARY KEY REFERENCES checklists(id),
  comeu_bem BOOLEAN,
  aceitou TEXT[],
  recusou TEXT[],
  comeu_sentado BOOLEAN,
  utensilio TEXT CHECK (utensilio IN ('colher', 'garfo', 'mao', 'misto'))
);

-- Comunicação
CREATE TABLE checklist_comunicacao (
  checklist_id UUID PRIMARY KEY REFERENCES checklists(id),
  usou_gestos BOOLEAN,
  palavras_ditas TEXT[],
  apontou BOOLEAN,
  puxou_mao TEXT CHECK (puxou_mao IN ('nunca', 'às_vezes', 'maioria', 'sempre')),
  respondeu_nome TEXT CHECK (respondeu_nome IN ('nunca', 'às_vezes', 'sempre')),
  imitou BOOLEAN
);

-- Brincar
CREATE TABLE checklist_brincar (
  checklist_id UUID PRIMARY KEY REFERENCES checklists(id),
  com_que_brincou TEXT[],
  modo TEXT CHECK (modo IN ('sozinho', 'com_adulto', 'misto')),
  fez_faz_de_conta BOOLEAN,
  tempo_sem_tela_minutos INTEGER
);

-- Higiene
CREATE TABLE checklist_higiene (
  checklist_id UUID PRIMARY KEY REFERENCES checklists(id),
  banho TEXT CHECK (banho IN ('tranquilo', 'resistencia', 'crise')),
  escovou_dentes BOOLEAN,
  sinalizou_banheiro BOOLEAN
);

-- Vestuário
CREATE TABLE checklist_vestuario (
  checklist_id UUID PRIMARY KEY REFERENCES checklists(id),
  colaborou_roupa BOOLEAN,
  incomodo_sensorial BOOLEAN
);

-- Movimento
CREATE TABLE checklist_movimento (
  checklist_id UUID PRIMARY KEY REFERENCES checklists(id),
  atividades TEXT[],
  caiu_muito BOOLEAN,
  buscou_colo BOOLEAN
);

-- Humor e regulação
CREATE TABLE checklist_humor (
  checklist_id UUID PRIMARY KEY REFERENCES checklists(id),
  humor_geral TEXT CHECK (humor_geral IN ('muito_bom', 'bom', 'regular', 'agitado', 'difícil')),
  teve_crise BOOLEAN,
  o_que_acalmou TEXT,
  notas TEXT
);

-- Participação na rotina
CREATE TABLE checklist_rotina (
  checklist_id UUID PRIMARY KEY REFERENCES checklists(id),
  guardou_brinquedos BOOLEAN,
  ajudou_tarefa BOOLEAN,
  aceitou_transicao BOOLEAN
);

-- Observações livres
CREATE TABLE checklist_observacoes (
  checklist_id UUID PRIMARY KEY REFERENCES checklists(id),
  conquistas TEXT,
  dificuldades TEXT,
  diferente_hoje TEXT
);

-- Terapias (Desacopladas)
CREATE TABLE sessoes_terapia (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  crianca_id UUID REFERENCES criancas(id),
  usuario_id UUID REFERENCES usuarios(id),
  data DATE NOT NULL,
  horario_inicio TIME,
  horario_fim TIME,
  especialidade TEXT NOT NULL,
  notas_sessao TEXT,
  criado_em TIMESTAMPTZ DEFAULT NOW(),
  atualizado_em TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 4.5 Mídia — Áudios e Vídeos

```sql
CREATE TABLE midias (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  crianca_id UUID REFERENCES criancas(id),
  usuario_id UUID REFERENCES usuarios(id),
  tipo TEXT CHECK (tipo IN ('audio', 'video', 'foto')),
  contexto TEXT CHECK (contexto IN ('checklist', 'registro_livre', 'sessao')),
  checklist_id UUID REFERENCES checklists(id),
  storage_path TEXT NOT NULL,
  duracao_segundos INTEGER,
  transcricao TEXT,
  analise_agente TEXT,
  processado BOOLEAN DEFAULT FALSE,
  criado_em TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 4.6 Atividades Propostas

```sql
CREATE TABLE atividades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID REFERENCES accounts(id),
  criada_por UUID REFERENCES usuarios(id),
  titulo TEXT NOT NULL,
  descricao TEXT NOT NULL,
  tipo TEXT CHECK (tipo IN (
    'brincadeira', 'alimentacao', 'comunicacao',
    'motor', 'higiene', 'rotina'
  )),
  objetivo TEXT,
  materiais TEXT[],
  duracao_minutos INTEGER,
  criado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE atividades_criancas (
  atividade_id UUID REFERENCES atividades(id),
  crianca_id UUID REFERENCES criancas(id),
  recomendada_por UUID REFERENCES usuarios(id),
  data_recomendacao DATE DEFAULT CURRENT_DATE,
  status TEXT CHECK (status IN ('pendente', 'em_andamento', 'concluida')),
  feedback TEXT,
  PRIMARY KEY (atividade_id, crianca_id)
);
```

---

### 4.7 Perfil Vivo da Criança

```sql
-- Atualizado automaticamente pelo agente após cada checklist e documento
CREATE TABLE perfil_crianca (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  crianca_id UUID UNIQUE REFERENCES criancas(id),
  atualizado_em TIMESTAMPTZ DEFAULT NOW(),
  comunicacao JSONB DEFAULT '{}',
  motor JSONB DEFAULT '{}',
  alimentacao JSONB DEFAULT '{}',
  sono JSONB DEFAULT '{}',
  regulacao JSONB DEFAULT '{}',
  resumo_geral TEXT
);
```

**Exemplo de perfil vivo do Bernardo:**

```json
{
  "comunicacao": {
    "gestos": "aponta com consistência desde mar/25",
    "palavras_ativas": ["da", "não", "mamã", "água"],
    "combinacao_gesto_palavra": false,
    "puxar_mao": "reduzindo — era 'maioria' em jan, 'às_vezes' em jun",
    "respondeu_nome": "às_vezes"
  },
  "motor": {
    "grosso": "corre, sobe escadas, dança — sem grandes dificuldades",
    "fino": "usa colher de forma independente na maior parte do tempo"
  },
  "alimentacao": {
    "aceita_bem": ["arroz", "frango", "fruta"],
    "recusa_frequente": ["legumes verdes", "texturas pastosas"],
    "utensilio": "misto, preferência pela mão"
  },
  "sono": {
    "media_horas": 10,
    "acorda_noite": "ocasionalmente"
  },
  "regulacao": {
    "gatilhos_crise": ["retirada de tela", "transições abruptas"],
    "o_que_acalma": ["colo", "música", "objeto favorito"]
  },
  "resumo_geral": "Bernardo, 2a 8m, atraso de fala e desenvolvimento. Ponto forte: vínculo afetivo e curiosidade. Em trabalho: linguagem expressiva, transições e tolerância sensorial."
}
```

---

## 5. Fluxos Principais

### 5.1 Ingestão de PDF (laudo ou relatório)

```
1. python ingest.py --file "laudo_fono.pdf" --tipo laudo
                    --especialidade fono --data 2025-06-10
                    --profissional "Dra. Ana"

2. Pipeline:
   ├── Salva arquivo no storage (R2 / Supabase Storage)
   ├── Extrai texto com pypdf
   ├── Divide em chunks (~500 tokens com overlap)
   ├── Gera embeddings para cada chunk (via API do LLM)
   ├── Salva chunks + embeddings em documento_chunks
   └── Atualiza perfil_crianca via agente:
       "Com base nesse laudo, atualize o perfil vivo."

3. Confirmação no terminal:
   "Laudo da fono de jun/25 indexado. 12 chunks gerados.
    Perfil atualizado: palavras ativas atualizadas para 7."
```

---

### 5.2 Ingestão de Áudio (checklist por voz)

```
1. python ingest.py --file "dia_bernardo_15jun.m4a"
                    --tipo audio --contexto checklist

2. Pipeline:
   ├── Transcreve com Whisper local
   ├── Envia transcrição para o agente:
   │   "Extraia os campos do checklist diário desse texto.
   │    Retorne JSON com os campos preenchidos e uma lista
   │    dos campos ausentes."
   ├── Agente retorna JSON estruturado (sem perguntar por campos faltantes)
   ├── Salva checklist no banco usando UPSERT (concatena novos dados aos existentes no dia)
   └── Exibe no terminal/WhatsApp apenas uma confirmação leve:
       "Anotado! ✅"

3. Se houverem novos relatos ao longo do dia, eles são enviados isoladamente e o banco se encarrega de acumular as informações (ex: arrays são concatenados via `array_cat`).
```

---

### 5.3 Ingestão de Vídeo

```
1. python ingest.py --file "almoco_jun15.mp4"
                    --tipo video --contexto checklist

2. Pipeline:
   ├── Extrai frames (1 por segundo)
   ├── Extrai e transcreve áudio com Whisper
   ├── Envia frames + transcrição para modelo multimodal:
   │   "Descreva o que está acontecendo nesse vídeo
   │    no contexto de desenvolvimento infantil.
   │    Foque em: alimentação, comunicação, motor,
   │    regulação emocional."
   ├── Salva análise em midias.analise_agente
   └── Se contexto == checklist:
       preenche campos relevantes do checklist do dia
```

---

### 5.4 Consulta ao Agente (terminal)

```python
# chat.py
python chat.py --crianca bernardo

> Como foi a comunicação do Bernardo nas últimas 4 semanas?
> O que a fono disse sobre contato visual?
> Quais palavras novas surgiram em junho?
> Compare o sono de maio com junho.
> Sugira uma atividade para estimular o apontar.
```

O agente usa:
1. **Perfil vivo** como contexto fixo no system prompt
2. **Busca semântica** em documento_chunks para perguntas sobre laudos
3. **Queries SQL** em checklists para perguntas sobre séries temporais

---

### 5.5 Atualização Automática do Perfil Vivo

Disparada após qualquer ingestão (checklist, PDF, vídeo):

```python
# profile.py
def atualizar_perfil(crianca_id: str):
    # 1. Busca últimos 30 dias de checklists
    # 2. Busca documentos indexados dos últimos 90 dias
    # 3. Monta prompt para o agente:
    prompt = f"""
    Perfil atual: {perfil_atual}
    
    Novos dados (últimos 30 dias):
    - Checklists: {resumo_checklists}
    - Documentos novos: {resumo_documentos}
    
    Atualize o perfil vivo da criança.
    Retorne JSON com os mesmos campos, atualizados.
    Seja específico sobre tendências (melhorou, piorou,
    estável) e cite datas quando relevante.
    """
    # 4. Salva perfil atualizado em perfil_crianca
```

---

## 6. Agente — System Prompt Base

```
Você é o Manolo, assistente de acompanhamento do desenvolvimento de {nome_crianca}.

PERFIL ATUAL:
{perfil_vivo}

Você tem acesso ao histórico completo: laudos, relatórios de sessão,
avaliações padronizadas e registros diários.

Ao responder:
- Seja específico e cite datas quando relevante
- Identifique padrões e tendências ao longo do tempo
- Se a pergunta envolver laudos, busque nos documentos
- Se a pergunta envolver evolução diária, busque nos checklists
- Quando propor atividades, baseie-se nos materiais dos terapeutas
  e no perfil atual da criança
- Responda em português, de forma clara e acolhedora para a família

Perfil do usuário atual: {perfil_usuario}
Especialidade (se terapeuta): {especialidade}
```

---

## 7. Autenticação e Segurança (Fases 3 e 4.1)

O sistema possui duas camadas de segurança distintas:

**WhatsApp (Fase 3):**
Autenticação por número de telefone autorizado. A gestão é feita manualmente no banco via tabela `usuarios`. O webhook (`channels/main.py`) valida se o telefone recebido pertence a um usuário ativo antes de acionar o LangGraph.

**Web App (Fase 4.1):**
Implementação de JWT via cookies para proteger a interface gráfica (`/dashboard/*`).
- O `middleware.ts` no Next.js garante que páginas privadas só abram com cookie válido.
- O backend REST (`channels/api.py` e `core/security.py`) emite o JWT, realiza hash de senhas (`bcrypt`) e gerencia endpoints de `/login` e `/logout`.

## 8. Roadmap de Funcionalidades

### MVP (Fase 1 — local) — [Concluído]
- [x] Docker Compose local com Postgres + pgvector
- [x] Script de ingestão de PDF, áudio e vídeo
- [x] Agente via terminal e testes via Telegram

### Fase 2 — Nuvem — [Concluído]
- [x] Deploy do backend no Render/Railway
- [x] Banco no Supabase ou Neon
- [x] Storage no R2 ou Supabase Storage

### Fase 3 — WhatsApp + LangGraph — [Concluído]
- [x] Webhook configurado na Meta for Developers
- [x] Grafo simplificado (4 nós, UPSERT cumulativo, extração silenciosa)
- [x] Roteamento de intenção e RAG temporal
- [x] Consultas e relatórios sob demanda

### Fase 4 e 4.1 — Web App e Segurança — [Concluído]
- [x] Dashboard de evolução temporal (Next.js, Recharts)
- [x] Autenticação JWT via cookies (middleware.ts)
- [x] API REST para consumo do frontend
- [x] Upload de PDFs

---

## 9. Considerações de Privacidade (LGPD)

- Dados de saúde de criança — categoria sensível
- Isolamento por `account_id` em todas as tabelas
- Acesso de terapeutas limitado à sua especialidade
- Nenhum dado compartilhado entre contas
- Vídeos e áudios armazenados em storage privado (sem URL pública)
- Em produção: banco com SSL obrigatório, storage com acesso autenticado

---

## 9.1 Observabilidade (LangSmith)

Todo o rastreamento das chamadas da OpenAI e fluxo de pensamento do LLM é registrado no LangSmith:
- Utiliza-se o wrapper `wrap_openai` no cliente compartilhado (`core/clients.py`) para coletar traces finos diretamente das chamadas LLM.
- Os nós do LangGraph e as funções de ingestão são decoradas com `@traceable(name="...")` para organizar o fluxo de execução.
- Permite debugar alucinações, vazamentos de contexto temporal e latência de execução com precisão.

---

## 10. Seed — Dados Iniciais

Execute após criar todas as tabelas. Substitua os valores entre `< >` pelos reais.

```sql
-- 1. Conta da família
INSERT INTO accounts (id, nome, tipo)
VALUES (
  'a0000000-0000-0000-0000-000000000001',
  'Família Bernardo',
  'família'
);

-- 2. Pai — admin
INSERT INTO usuarios (id, account_id, nome, telefone_whatsapp, perfil)
VALUES (
  'u0000000-0000-0000-0000-000000000001',
  'a0000000-0000-0000-0000-000000000001',
  '<Seu Nome>',
  '<5511999999991>',
  'admin'
);

-- 3. Mãe — família
INSERT INTO usuarios (id, account_id, nome, telefone_whatsapp, perfil)
VALUES (
  'u0000000-0000-0000-0000-000000000002',
  'a0000000-0000-0000-0000-000000000001',
  '<Nome da Mãe>',
  '<5511999999992>',
  'família'
);

-- 4. Fonoaudióloga — terapeuta
INSERT INTO usuarios (id, account_id, nome, telefone_whatsapp, perfil)
VALUES (
  'u0000000-0000-0000-0000-000000000003',
  'a0000000-0000-0000-0000-000000000001',
  '<Nome da Fono>',
  '<5511999999993>',
  'terapeuta'
);

-- 5. Terapeuta Ocupacional
INSERT INTO usuarios (id, account_id, nome, telefone_whatsapp, perfil)
VALUES (
  'u0000000-0000-0000-0000-000000000004',
  'a0000000-0000-0000-0000-000000000001',
  '<Nome da TO>',
  '<5511999999994>',
  'terapeuta'
);

-- 6. Bernardo
INSERT INTO criancas (id, account_id, nome, data_nascimento, diagnosticos)
VALUES (
  'c0000000-0000-0000-0000-000000000001',
  'a0000000-0000-0000-0000-000000000001',
  'Bernardo',
  '<2022-10-01>',  -- substitua pela data real
  '["atraso de fala", "atraso de desenvolvimento"]'
);

-- 7. Vínculo Bernardo <-> terapeutas
INSERT INTO criancas_terapeutas (crianca_id, usuario_id, especialidade)
VALUES
  ('c0000000-0000-0000-0000-000000000001', 'u0000000-0000-0000-0000-000000000003', 'fono'),
  ('c0000000-0000-0000-0000-000000000001', 'u0000000-0000-0000-0000-000000000004', 'TO');

-- 8. Perfil vivo inicial do Bernardo (preencha com o que já sabe hoje)
INSERT INTO perfil_crianca (crianca_id, comunicacao, motor, alimentacao, sono, regulacao, resumo_geral)
VALUES (
  'c0000000-0000-0000-0000-000000000001',
  '{
    "gestos": "aponta com consistência",
    "palavras_ativas": ["da", "não", "mamã"],
    "combinacao_gesto_palavra": false,
    "puxar_mao": "frequente",
    "respondeu_nome": "às_vezes"
  }',
  '{
    "grosso": "corre, sobe escadas, dança",
    "fino": "usa colher com assistência"
  }',
  '{
    "aceita_bem": [],
    "recusa_frequente": [],
    "utensilio": "mão"
  }',
  '{
    "media_horas": 10,
    "acorda_noite": "ocasionalmente"
  }',
  '{
    "gatilhos_crise": ["retirada de tela", "transições abruptas"],
    "o_que_acalma": ["colo", "música"]
  }',
  'Bernardo, atraso de fala e desenvolvimento. Em acompanhamento com fono e TO. Perfil inicial — será enriquecido conforme laudos e checklists forem indexados.'
);
```

---

## 11. Contexto da Criança Piloto

**Nome:** Bernardo
**Diagnóstico:** Atraso de desenvolvimento e fala
**Terapias:** Fonoaudiologia, Terapia Ocupacional
**Avaliações realizadas:** Bayley-4
**Família:** Pai (admin, Tech Lead de IA), Mãe

Este documento foi gerado a partir de uma sessão de refinamento de produto entre o pai do Bernardo e o assistente Claude (Anthropic). Todas as decisões de arquitetura registradas aqui refletem escolhas deliberadas com justificativa documentada.
