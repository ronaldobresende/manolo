# Plano de Refatoração da Plataforma de IA do Manolo

> Objetivo: transformar o Manolo em uma plataforma AI-Native desacoplada dos modelos e provedores de IA, preparada para evolução contínua, redução de custos, observabilidade e suporte a múltiplos agentes.

---

# Objetivos

Ao final da refatoração, o sistema deverá permitir:

- trocar modelos sem alterar código de negócio;
- trocar provedores (OpenAI, Gemini, Claude...) apenas por configuração;
- suportar diferentes capacidades de cada modelo;
- reduzir custos de tokens;
- facilitar benchmark entre modelos;
- facilitar testes;
- preparar o sistema para workflows multiagente.

---

# Arquitetura Alvo

```
                 LangGraph
                     │
                     ▼
              AI Service Layer
                     │
         ┌───────────┼────────────┐
         ▼           ▼            ▼
  Prompt Layer   Model Registry  Provider Layer
                     │
          Capability Adapter
                     │
      ┌──────────────┼──────────────┐
      ▼              ▼              ▼
   OpenAI        Gemini        Claude
```

Nenhum nó do LangGraph deve conhecer OpenAI, Gemini ou Claude.

---

# Fase 1 — AI Service

Criar uma camada única responsável por toda comunicação com IA.

Exemplo:

```
AIService

chat()

structured_output()

classify()

summarize()

embeddings()

transcribe()
```

O restante da aplicação nunca chama diretamente a SDK do provedor.

Exemplo

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

Provider
```

---

# Fase 2 — Model Registry

Toda tarefa possuirá uma configuração centralizada.

Exemplo conceitual

```
Routing

Extraction

RAG

Summary

Profile

OCR

Backfill
```

Cada configuração define:

- provider
- modelo
- reasoning desejado
- temperatura desejada
- timeout
- retries
- structured output
- streaming
- cache

Assim, trocar GPT-5 por GPT-4o passa a ser apenas alteração de configuração.

---

# Fase 3 — Capability Adapter (IMPORTANTE)

Modelos diferentes possuem capacidades diferentes.

Exemplo

GPT-5

- suporta reasoning
- não suporta temperature

GPT-4o

- suporta temperature
- não suporta reasoning

Gemini

- possui parâmetros próprios

Claude

- possui parâmetros próprios

O sistema nunca deve assumir que todos possuem os mesmos parâmetros.

Criar uma camada responsável por adaptar automaticamente a configuração.

Exemplo conceitual

```
Task Configuration

↓

Capability Adapter

↓

Requisição compatível com o modelo escolhido
```

Exemplo

Configuração da tarefa

```
temperature = 0

reasoning = high
```

Se o modelo for GPT-5

↓

envia apenas

```
reasoning = high
```

Se o modelo for GPT-4o

↓

envia apenas

```
temperature = 0
```

Se amanhã surgir GPT-6 ou Gemini 4, basta atualizar o adapter.

Essa camada elimina completamente erros de incompatibilidade de parâmetros.

---

# Fase 4 — Provider Layer

Criar adapters para cada provedor.

Interface comum

```
generate()

structured_output()

embeddings()

transcribe()
```

Implementações

```
OpenAIProvider

GeminiProvider

ClaudeProvider
```

A lógica de negócio nunca conhece o provedor.

---

# Fase 5 — Prompt Layer

Todos os prompts devem sair do código.

Estrutura sugerida

```
prompts/

routing.md

checklist.md

rag.md

summary.md

profile.md

ocr.md
```

Benefícios

- versionamento
- revisão
- Prompt Engineering
- testes A/B
- reutilização

---

# Fase 6 — Responses API

Migrar gradualmente da Chat Completions API para Responses API onde fizer sentido.

Prioridade

- GPT-5
- Structured Outputs
- Reasoning
- Ferramentas futuras

Manter uma camada de abstração para permitir fallback caso seja necessário utilizar Chat Completions.

---

# Fase 7 — Prompt Builder

Hoje praticamente todos os prompts utilizam o mesmo contexto.

Criar um Prompt Builder.

Exemplo

```
PromptBuilder

↓

Prompt pequeno

↓

Routing

OCR

Data Parsing
```

ou

```
Prompt completo

↓

RAG

Perfil Vivo
```

Evitar enviar Perfil Vivo quando não for necessário.

Reduz custo significativamente.

---

# Fase 8 — Router Híbrido

Nem toda mensagem precisa de LLM.

Criar uma etapa determinística.

```
Mensagem

↓

Regras

↓

LLM
```

Exemplos

- oi
- bom dia
- obrigado
- ok
- 👍

Não precisam consumir tokens.

---

# Fase 9 — Retriever Inteligente

Hoje o RAG sempre busca:

- documentos
- checklists

Criar um Retriever que escolha apenas o contexto necessário.

Fluxo

```
Pergunta

↓

Retriever

↓

Contexto relevante

↓

LLM
```

---

# Fase 10 — Atualização do Perfil Vivo

Hoje ocorre logo após salvar um checklist.

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

Perfil Vivo
```

A resposta ao WhatsApp não deve depender dessa atualização.

---

# Fase 11 — Observabilidade

Centralizar métricas.

Registrar

- modelo
- provider
- latência
- tokens
- custo
- retries
- falhas
- cache hit
- reasoning utilizado

Permitir dashboards por tarefa.

---

# Fase 12 — Prompt Versioning

Versionar prompts.

Exemplo

```
routing_v1

routing_v2

routing_v3
```

Permite rollback sem alterar código.

---

# Fase 13 — Testes

Criar suíte de testes para IA.

Routing

- classificação correta

Extraction

- JSON válido

RAG

- grounding
- guardrails
- datas relativas

Summary

- tom adequado

Profile

- evolução longitudinal

---

# Fase 14 — Benchmark

Criar ferramenta para comparar modelos.

Exemplo

Mesma entrada

↓

GPT-5

↓

GPT-4o

↓

Gemini

↓

Claude

Comparar

- qualidade
- custo
- latência
- tokens

---

# Fase 15 — Multiagentes

Preparar arquitetura para agentes especializados.

```
Supervisor

│

├── Routing Agent

├── Checklist Agent

├── RAG Agent

├── Summary Agent

├── Profile Agent

└── OCR Agent
```

Todos utilizam

- AIService
- Prompt Layer
- Model Registry
- Capability Adapter
- Provider Layer

---

# Roadmap

## Sprint 1

- AIService
- Model Registry
- Capability Adapter
- GPT-5
- Responses API

---

## Sprint 2

- Provider Layer
- Prompt Layer
- Observabilidade
- Retry Policy

---

## Sprint 3

- Prompt Builder
- Router híbrido
- Retriever inteligente
- Cache

---

## Sprint 4

- Eventos para Perfil Vivo
- Benchmark
- Prompt Versioning
- Métricas de custo

---

## Sprint 5

- Arquitetura Multiagente
- Supervisor
- Especialização de agentes

---

# Benefícios Esperados

Ao final da refatoração, o Manolo terá uma arquitetura desacoplada e preparada para evolução contínua. A troca de modelos (GPT-5, GPT-4o, Gemini, Claude ou futuros) deixará de exigir alterações na lógica de negócio, passando a ser apenas uma mudança de configuração. O sistema será resiliente às diferenças de capacidades entre modelos (como `temperature`, `reasoning` e outros parâmetros), permitindo benchmark contínuo, redução de custos, maior observabilidade e uma base sólida para a evolução para workflows multiagente.