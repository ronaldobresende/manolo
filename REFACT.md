# Plano de Refatoração da Plataforma de IA do Manolo

> **Objetivo:** transformar o Manolo em uma plataforma AI-Native desacoplada de modelos, prompts e provedores de IA, permitindo evoluir continuamente entre OpenAI, Gemini, Claude e futuros modelos apenas por configuração, preservando a lógica de negócio e reduzindo o custo de manutenção.

---

# Princípios da Arquitetura

A arquitetura deverá seguir os seguintes princípios:

- A lógica de negócio nunca conhece o modelo utilizado.
- A lógica de negócio nunca conhece o provedor de IA.
- Prompts são tratados como artefatos versionáveis.
- Cada família de modelos pode possuir prompts próprios.
- A troca de modelo deve ocorrer apenas por configuração.
- A plataforma deve adaptar automaticamente diferenças entre modelos (temperature, reasoning, etc.).
- O LangGraph deve conhecer apenas tarefas de negócio.

---

# Arquitetura Alvo

```text
                 LangGraph
                     │
                     ▼
                AI Service
                     │
         ┌───────────┼────────────┐
         ▼           ▼            ▼
 Prompt Builder   AI Profiles   Provider Layer
                     │
             Capability Adapter
                     │
      ┌──────────────┼──────────────┐
      ▼              ▼              ▼
   OpenAI        Gemini        Claude
```

---

# Fase 1 — AI Service

## Objetivo

Criar uma camada única responsável por toda comunicação com modelos de IA.

Nenhum nó do LangGraph poderá chamar diretamente:

- OpenAI
- Gemini
- Claude

Toda comunicação deverá passar pelo AIService.

Exemplo de responsabilidades:

- geração de texto;
- structured outputs;
- classificação;
- embeddings;
- transcrição;
- retries;
- logging;
- métricas;
- streaming.

---

# Fase 2 — AI Profiles

## Objetivo

Substituir a configuração direta de modelos por perfis de IA.

Ao invés de uma tarefa conhecer um modelo específico, ela conhecerá apenas um perfil.

Exemplo conceitual

```
Routing

↓

routing-gpt5
```

Cada perfil define:

- provider
- modelo
- prompt
- reasoning
- temperature
- timeout
- retries
- structured output
- cache
- streaming

Exemplo

```
routing-gpt5

↓

OpenAI

↓

GPT-5 Nano

↓

Prompt GPT-5

↓

Reasoning Low
```

Outro perfil

```
routing-gpt4

↓

OpenAI

↓

GPT-4o Mini

↓

Prompt GPT-4

↓

Temperature 0
```

Outro perfil

```
routing-gemini

↓

Gemini

↓

Prompt Gemini
```

A troca entre modelos passa a ser apenas alteração de configuração.

Nenhuma linha da lógica de negócio precisa ser modificada.

---

# Fase 3 — Capability Adapter

## Objetivo

Cada modelo possui capacidades diferentes.

Exemplos

GPT-5

- reasoning
- sem temperature

GPT-4o

- temperature
- sem reasoning

Gemini

- safety settings

Claude

- thinking

O Capability Adapter adapta automaticamente a configuração do AI Profile para o provedor escolhido.

Fluxo

```
AI Profile

↓

Capability Adapter

↓

Requisição compatível
```

Exemplo

Configuração

```
temperature = 0

reasoning = high
```

GPT-5

↓

envia

```
reasoning = high
```

GPT-4o

↓

envia

```
temperature = 0
```

O restante do sistema permanece totalmente transparente a essas diferenças.

---

# Fase 4 — Provider Layer

Criar adapters para cada provedor.

Todos deverão implementar a mesma interface.

Exemplo conceitual

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

O restante da plataforma nunca conhecerá a SDK utilizada.

---

# Fase 5 — Prompt Layer

Todos os prompts deverão sair do código.

Estrutura sugerida

```
ai/

prompts/

gpt4/

gpt5/

gemini/

claude/
```

Cada família de modelos poderá possuir prompts próprios.

Exemplo

```
gpt5/

routing.md

rag.md

summary.md

profile.md
```

```
gpt4/

routing.md

rag.md

summary.md
```

Isso permite otimizar prompts individualmente para cada família de modelos.

---

# Fase 6 — Prompt Builder

O Prompt Builder será responsável por montar automaticamente o prompt final.

Hoje vários prompts são montados manualmente.

O Prompt Builder combinará:

- prompt base;
- guardrails;
- contexto;
- Perfil Vivo;
- persona;
- especialidade.

Fluxo

```
Base

+

Guardrails

+

Contexto

+

Perfil

+

Persona

↓

Prompt Final
```

Nenhum nó do LangGraph deverá concatenar prompts manualmente.

---

# Fase 7 — Versionamento de Prompts

Os prompts passam a ser tratados como código.

O versionamento principal será realizado pelo Git.

Cada AI Profile referencia explicitamente o prompt adequado para aquela família de modelos.

Exemplo

```
routing-gpt5

↓

prompts/gpt5/routing.md
```

```
routing-gpt4

↓

prompts/gpt4/routing.md
```

Caso seja necessário retornar do GPT-5 para GPT-4, basta alterar o AI Profile.

O sistema utilizará automaticamente:

- o modelo correto;
- o prompt correto;
- a configuração correta.

---

# Fase 8 — Responses API

Migrar gradualmente da Chat Completions API para Responses API.

Benefícios

- GPT-5
- reasoning
- structured outputs
- ferramentas futuras

A camada de Provider deverá esconder essa diferença.

---

# Fase 9 — Router Híbrido

Nem toda mensagem precisa consumir tokens.

Criar uma etapa determinística.

Fluxo

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
- 👍

podem ser respondidos sem utilização de IA.

---

# Fase 10 — Retriever Inteligente

Hoje o RAG busca sempre os mesmos conjuntos de dados.

Criar um Retriever responsável por decidir qual contexto enviar.

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

Reduz tokens e melhora qualidade.

---

# Fase 11 — Prompt Cache

Alguns componentes do prompt mudam muito pouco.

Exemplos

- Perfil Vivo
- Prompt Base
- Especialidade
- Perfil do Usuário

Esses componentes poderão ser mantidos em cache para reduzir:

- tempo de resposta;
- custo;
- reconstrução de prompts.

---

# Fase 12 — Atualização do Perfil Vivo

Hoje o Perfil Vivo é atualizado logo após o fluxo principal.

Migrar para arquitetura orientada a eventos.

Fluxo

```
Checklist salvo

↓

Evento

↓

Fila

↓

Worker

↓

Atualizar Perfil Vivo
```

A resposta ao WhatsApp não deverá depender desse processamento.

---

# Fase 13 — Observabilidade

Centralizar métricas da IA.

Registrar

- provider;
- modelo;
- AI Profile utilizado;
- prompt utilizado;
- latência;
- tokens;
- custo;
- retries;
- falhas;
- cache hit;
- reasoning utilizado.

Permitir dashboards por tarefa.

---

# Fase 14 — Benchmark

Criar ferramenta para comparação de modelos.

Mesmo prompt

↓

Mesmo contexto

↓

GPT-5

↓

GPT-4o

↓

Gemini

↓

Claude

Comparar

- qualidade;
- latência;
- custo;
- tokens.

Isso permitirá trocar modelos com base em evidências.

---

# Fase 15 — Testes

Criar suíte de testes para IA.

Routing

- classificação correta.

Extraction

- JSON válido.

RAG

- grounding;
- datas relativas;
- guardrails.

Summary

- tom adequado.

Perfil Vivo

- evolução longitudinal;
- consolidação de informações.

---

# Fase 16 — Preparação para Multiagentes

A arquitetura deverá permitir evolução para múltiplos agentes especializados.

Exemplo

```
Supervisor

│

├── Routing Agent

├── Checklist Agent

├── RAG Agent

├── Summary Agent

├── Profile Agent

├── OCR Agent

└── Analytics Agent
```

Todos compartilharão:

- AI Service;
- AI Profiles;
- Prompt Builder;
- Provider Layer;
- Capability Adapter;
- Observabilidade.

---

# Roadmap

## Sprint 1

- AI Service
- AI Profiles
- Capability Adapter
- Migração para GPT-5
- Responses API

---

## Sprint 2

- Provider Layer
- Prompt Layer
- Prompt Builder
- Observabilidade

---

## Sprint 3

- Router híbrido
- Retriever Inteligente
- Prompt Cache
- Benchmark

---

## Sprint 4

- Eventos para Perfil Vivo
- Testes automatizados
- Métricas de custo
- Dashboards

---

## Sprint 5

- Arquitetura Multiagente
- Supervisor
- Especialização de agentes

---

# Benefícios Esperados

Ao final da refatoração, o Manolo possuirá uma arquitetura verdadeiramente AI-Native, desacoplada da tecnologia de IA utilizada.

A mudança entre GPT-5, GPT-4o, Gemini, Claude ou futuros modelos será realizada apenas pela troca de um **AI Profile**, que encapsula modelo, provedor, prompt e parâmetros específicos da família de modelos. A lógica de negócio permanecerá inalterada.

Essa arquitetura permitirá:

- migração segura entre modelos;
- rollback imediato para modelos anteriores;
- prompts específicos para cada família de modelos;
- adaptação automática às capacidades de cada provedor;
- redução do acoplamento;
- maior observabilidade;
- benchmarking contínuo;
- preparação para uma plataforma multiagente escalável.