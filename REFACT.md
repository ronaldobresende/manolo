# Plano de Refatoração — Manolo AI Platform

> Objetivo: evoluir a arquitetura atual do Manolo para uma plataforma AI-Native, preparada para múltiplos modelos, múltiplos provedores (OpenAI, Gemini, Claude), LangGraph e futuras capacidades de Agentes de IA, reduzindo acoplamento, custo operacional e complexidade de manutenção.

---

# Objetivos da Refatoração

A arquitetura atual encontra-se funcional e organizada, porém ainda possui forte acoplamento entre:

- LangGraph
- OpenAI
- Prompts
- Modelos
- Regras de negócio

O objetivo desta refatoração é separar claramente essas responsabilidades para que a IA torne-se apenas uma dependência da aplicação, e não parte da lógica de negócio.

Ao final da refatoração espera-se:

- trocar modelos sem alterar regras de negócio;
- trocar provedor (OpenAI, Gemini, Claude...) sem alterar os agentes;
- reduzir custo de tokens;
- facilitar testes;
- facilitar observabilidade;
- preparar o sistema para workflows multi-agente.

---

# Prioridade Geral

## Fase 1 (Obrigatória)

Arquitetura

## Fase 2

LLM Layer

## Fase 3

Prompt Layer

## Fase 4

Otimização

## Fase 5

Agentes Avançados

---

# Fase 1 — Desacoplamento da IA

## Objetivo

Nenhum nó do LangGraph deve conhecer OpenAI.

Hoje existem chamadas como:

```python
client.chat.completions.create(...)
```

ou

```python
client.beta.chat.completions.parse(...)
```

espalhadas pelo projeto.

Toda comunicação com modelos deve ser centralizada.

---

## Criar um AI Service

Exemplo:

```
AIService
│
├── chat()
├── structured_output()
├── classify()
├── summarize()
├── embeddings()
└── transcribe()
```

Os nós passam apenas:

- tarefa
- prompt
- contexto

e nunca mais o modelo.

Exemplo:

Antes

```
LangGraph
    ↓
OpenAI
```

Depois

```
LangGraph
      ↓
 AIService
      ↓
 Model Registry
      ↓
OpenAI / Gemini / Claude
```

---

# Fase 2 — Model Registry

Hoje os modelos estão espalhados em configurações.

Criar um registro único.

Exemplo:

```python
TASK_ROUTING

TASK_EXTRACTION

TASK_RAG

TASK_SUMMARY

TASK_PROFILE

TASK_OCR

TASK_BACKFILL
```

Cada tarefa define:

- modelo
- reasoning
- provider
- timeout
- retries

Exemplo conceitual

```
Routing

↓

GPT-5 Nano

Extraction

↓

GPT-5 Mini

RAG

↓

GPT-5

```

Trocar um modelo passa a exigir alteração em apenas um lugar.

---

# Fase 3 — Provider Layer

Criar adapters.

```
LLMProvider
```

Implementações

```
OpenAIProvider

GeminiProvider

ClaudeProvider
```

Todos implementam a mesma interface.

Exemplo

```
generate()

structured_output()

embeddings()

transcribe()
```

Assim o restante do projeto desconhece qual provedor está sendo utilizado.

---

# Fase 4 — Prompt Layer

Hoje praticamente todos os prompts estão hardcoded.

Mover para:

```
prompts/

routing.md

rag.md

summary.md

profile.md

checklist.md

ocr.md
```

Benefícios

- versionamento
- revisão
- testes
- Prompt Engineering
- A/B Testing

---

# Fase 5 — Responses API

Migrar gradualmente de:

```
chat.completions
```

para

```
Responses API
```

Benefícios

- GPT-5
- Reasoning
- Structured Outputs
- Ferramentas futuras

---

# Fase 6 — Configuração por tarefa

Cada tarefa possui uma configuração.

Exemplo conceitual

```
Routing

Modelo

Reasoning

Timeout

Retries

Temperature (quando suportado)

Structured Output
```

Nenhum nó define parâmetros do modelo.

---

# Fase 7 — Observabilidade

Adicionar métricas centralizadas.

Registrar:

- modelo
- latência
- tokens
- custo
- retries
- falhas
- provider

Permitir dashboards por tarefa.

Exemplo

```
Routing

2 ms

GPT-5 Nano

US$ 0.00001
```

---

# Fase 8 — Prompt Cache

Os prompts de sistema são reconstruídos diversas vezes.

Criar cache para:

- Perfil Vivo
- Prompt base
- Especialidade
- Perfil do usuário

Reduz tokens.

---

# Fase 9 — Retriever

Hoje o RAG sempre busca:

- documentos
- checklists

Criar um Retriever inteligente.

Exemplo

```
Pergunta

↓

Retriever

↓

Seleciona apenas contexto relevante

↓

LLM
```

Evita enviar contexto desnecessário.

---

# Fase 10 — Router híbrido

Hoje toda mensagem passa pelo LLM.

Criar duas camadas.

```
Mensagem

↓

Regras determinísticas

↓

LLM
```

Exemplos

- oi
- bom dia
- obrigado
- ok

não precisam consumir tokens.

---

# Fase 11 — Atualização do Perfil Vivo

Hoje ocorre após o término do fluxo.

Migrar para arquitetura orientada a eventos.

```
Checklist salvo

↓

Evento

↓

Fila

↓

Worker

↓

Atualização Perfil Vivo
```

Evita aumentar o tempo de resposta do WhatsApp.

---

# Fase 12 — Gestão de Prompts

Criar versionamento.

Exemplo

```
routing_v1

routing_v2

routing_v3
```

Permite rollback.

---

# Fase 13 — Testes

Criar testes para cada tarefa.

Exemplos

## Routing

Entrada

```
Hoje ele dormiu bem.
```

Saída esperada

```
checklist
```

---

## Extraction

Entrada

```
Dormiu das 13 às 15.
```

Validar JSON.

---

## RAG

Perguntas

Datas relativas

Guardrails

Diagnóstico

---

# Fase 14 — Custos

Criar relatório diário.

Por tarefa

- custo
- tokens
- latência

Por modelo

- GPT-5
- GPT-5 Mini
- GPT-5 Nano

---

# Fase 15 — Preparação para Multiagentes

A arquitetura deve permitir evolução para múltiplos agentes especializados.

Exemplo

```
Supervisor

│

├── Routing Agent

├── Checklist Agent

├── RAG Agent

├── Report Agent

├── Profile Agent

└── OCR Agent
```

Cada agente compartilha:

- AIService
- Prompt Layer
- Provider Layer
- Observabilidade

---

# Roadmap Sugerido

## Sprint 1

- AIService
- Model Registry
- Responses API
- GPT-5

---

## Sprint 2

- Prompt Layer
- Provider Layer
- Observabilidade
- Retry Policy

---

## Sprint 3

- Retriever Inteligente
- Router híbrido
- Cache
- Eventos para Perfil Vivo

---

## Sprint 4

- Prompt Versioning
- Métricas de custo
- Benchmark entre OpenAI, Gemini e Claude
- Preparação para arquitetura multiagente

---

# Resultado Esperado

Ao final da refatoração o Manolo deverá possuir uma arquitetura AI-Native desacoplada, modular e orientada a capacidades, onde regras de negócio, orquestração, modelos de IA e provedores estejam completamente separados. Isso permitirá evoluir continuamente os modelos utilizados (GPT-5, Gemini, Claude ou futuros), reduzir custos operacionais, aumentar a observabilidade e preparar a plataforma para agentes especializados e workflows multiagente sem necessidade de alterações significativas na lógica de negócio.