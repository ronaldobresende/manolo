# MANOLO — Prompt Web App (Fase 4)


> Modelo recomendado: Claude Sonnet 4.6 para arquitetura e integração com backend.
> Gemini Flash High para componentes visuais e UI.

---

## Prompt

```
Leia os arquivos MANOLO.md e MANOLO_STATUS.md na raiz do projeto
para entender o contexto completo antes de começar.

Vou construir a Fase 4 do projeto Manolo: um Web App em React
que se integra ao backend FastAPI já existente no Render.

## Contexto do projeto

O Manolo é um sistema de acompanhamento do desenvolvimento infantil.
Já está em produção com:
- Backend: FastAPI rodando no Render
- Banco: PostgreSQL 18 + pgvector no Neon
- Agente: LangGraph com 6 nós, RAG, checklist conversacional
- Canal: WhatsApp Business API
- Storage: Cloudflare R2
- Observabilidade: LangSmith + Sentry

O Web App é uma nova interface — não substitui o WhatsApp,
complementa com visualização e gestão.

## Stack do Web App

- React + Next.js (App Router)
- TypeScript
- Tailwind CSS
- Recharts para gráficos de evolução
- Deploy na Vercel (gratuito)
- Autenticação: email + senha via JWT
  (diferente do WhatsApp que usa número de telefone)

## O que o Web App deve ter

### 1. Autenticação
- Login com email + senha
- JWT armazenado em cookie httpOnly
- Perfis: admin, família, terapeuta
- Terapeutas veem só dados relevantes à sua especialidade

### 2. Dashboard principal (página inicial após login)
- Perfil vivo atual do Bernardo em cards por domínio:
  Comunicação, Motor, Alimentação, Sono, Regulação
- Resumo geral em texto
- Últimas conquistas (tabela marcos)
- Data da última atualização do perfil

### 3. Evolução temporal (gráficos)
Gráficos de linha por domínio ao longo do tempo, usando
dados dos checklists diários. Filtro por período:
última semana, último mês, últimos 3 meses, personalizado.

Domínios para visualizar:
- Sono: média de horas, frequência de acorde noturno
- Comunicação: palavras ditas por dia, uso de gestos,
  respondeu ao nome
- Humor: frequência de crises, humor geral
- Alimentação: aceitação alimentar, uso de utensílio
- Brincar: tempo sem tela, modo de brincar

### 4. Checklists
- Listagem dos checklists por data (tabela paginada)
- Visualização detalhada de um checklist específico
- Filtro por período e por campo

### 5. Documentos
- Listagem de laudos e relatórios indexados
- Upload de novo PDF com campos:
  tipo (laudo/relatório/avaliação), especialidade,
  título, data do documento
- Após upload: chamar endpoint do backend que dispara
  o pipeline de ingestão (ingestion_pdf.py)
- Status de processamento (processado: true/false)

### 6. Marcos e conquistas
- Listagem cronológica de todos os marcos registrados
- Formulário para registrar novo marco manualmente
- Campo: descrição, data

### 7. Atividades
- Listagem de atividades cadastradas pelos terapeutas
- Formulário para cadastrar nova atividade:
  título, descrição, tipo, objetivo, materiais, duração
- Status por criança: pendente, em andamento, concluída
- Campo de feedback da família

### 8. Chat com o agente (sidebar ou página dedicada)
- Campo de texto para digitar perguntas ao agente Manolo
- O frontend chama o backend FastAPI via HTTP POST
- O backend executa o grafo LangGraph e retorna a resposta
- Histórico da conversa exibido na interface
- Exemplos de perguntas sugeridas:
  "Como foi a comunicação essa semana?"
  "Prepara um resumo para a sessão de fono"
  "Compare o sono de maio com junho"

### 9. Gestão de usuários (só para admin)
- Listagem de usuários autorizados
- Formulário para adicionar novo usuário:
  nome, telefone WhatsApp, email, perfil, especialidade
- Toggle para ativar/desativar acesso

## Integração com o backend

O Web App chama o backend FastAPI via REST.
O backend já existe — o Web App não duplica lógica,
apenas consome as APIs.

Criar as seguintes rotas no backend (channels/main.py
ou novo arquivo api.py):

### Rotas a criar no backend

```
GET  /api/perfil/{crianca_id}
     → retorna perfil_crianca completo

GET  /api/checklists/{crianca_id}?inicio=&fim=
     → retorna lista de checklists com todas as seções

GET  /api/checklists/{crianca_id}/{data}
     → retorna checklist detalhado de uma data

GET  /api/documentos/{crianca_id}
     → retorna lista de documentos indexados

POST /api/documentos/{crianca_id}
     → recebe PDF multipart, dispara ingestion_pdf.py

GET  /api/marcos/{crianca_id}
     → retorna lista de marcos cronológicos

POST /api/marcos/{crianca_id}
     → registra novo marco

GET  /api/atividades/{crianca_id}
     → retorna atividades vinculadas à criança

POST /api/atividades
     → cadastra nova atividade

PATCH /api/atividades/{atividade_id}/status
     → atualiza status e feedback

POST /api/chat
     → body: {mensagem, crianca_id, telefone_whatsapp}
     → chama o agente LangGraph e retorna resposta

GET  /api/usuarios
     → lista usuários (só admin)

POST /api/usuarios
     → cadastra novo usuário

PATCH /api/usuarios/{id}/ativo
     → ativa ou desativa usuário
```

## Autenticação nas rotas

Todas as rotas /api/* exigem JWT válido no header:
Authorization: Bearer {token}

Criar endpoint:
POST /api/auth/login
     → body: {email, senha}
     → retorna JWT com payload: {usuario_id, perfil, especialidade}

Adicionar campo senha_hash à tabela usuarios no banco.
Usar bcrypt para hash.

## Estrutura de pastas do Web App

Criar dentro do monorepo existente:

```
manolo/
└── web/                    # Web App (Next.js)
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx        # redirect para /dashboard
    │   ├── login/
    │   │   └── page.tsx
    │   └── dashboard/
    │       ├── layout.tsx  # sidebar + header
    │       ├── page.tsx    # dashboard principal
    │       ├── evolucao/
    │       │   └── page.tsx
    │       ├── checklists/
    │       │   └── page.tsx
    │       ├── documentos/
    │       │   └── page.tsx
    │       ├── marcos/
    │       │   └── page.tsx
    │       ├── atividades/
    │       │   └── page.tsx
    │       ├── chat/
    │       │   └── page.tsx
    │       └── usuarios/
    │           └── page.tsx
    ├── components/
    │   ├── ui/             # componentes base (Button, Card, Input...)
    │   ├── charts/         # gráficos Recharts por domínio
    │   ├── perfil/         # cards do perfil vivo
    │   └── layout/         # Sidebar, Header, etc
    ├── lib/
    │   ├── api.ts          # funções de chamada ao backend
    │   └── auth.ts         # helpers de autenticação JWT
    ├── types/
    │   └── manolo.ts       # tipos TypeScript do projeto
    ├── package.json
    ├── next.config.js
    ├── tailwind.config.js
    └── tsconfig.json
```

## Ordem de implementação sugerida

1. Setup Next.js + Tailwind na pasta web/
2. Autenticação (login + JWT + middleware de proteção)
3. Rotas do backend (api.py no FastAPI)
4. Dashboard principal com perfil vivo
5. Gráficos de evolução (Recharts)
6. Listagem de checklists
7. Upload e listagem de documentos
8. Marcos e conquistas
9. Atividades
10. Chat com o agente
11. Gestão de usuários (admin)

## Restrições importantes

- Nunca duplicar lógica do backend no frontend
- Terapeutas não veem dados de outras especialidades
- Mensagens proativas nunca são enviadas automaticamente
  para terapeutas — sempre com confirmação do admin
- O campo senha_hash nunca é retornado nas respostas da API
- Dados do Bernardo são sensíveis (saúde de criança)
  — JWT com expiração de 8 horas, renovação automática

## Design

- Mobile-first — terapeutas vão acessar pelo celular
- Cores: tons de verde e bege — remetendo ao crescimento
- Fontes limpas, sem serifa
- Cards com bordas suaves, sem excesso de elementos visuais
- Dashboard deve parecer um relatório clínico bonito,
  não um painel de métricas de negócio
```
