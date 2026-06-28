# MANOLO — Status de Desenvolvimento

> Atualizar ao fim de cada sessão de desenvolvimento.
> Este arquivo é o contexto dinâmico do projeto — o que já foi feito, o que está em andamento e o que vem a seguir.

> O objetivo é ter um sistema de acompanhamento do desenvolvimento infantil via WhatsApp, com agente inteligente (LangGraph), checklist conversacional e base de conhecimento clínica.
---

## Última atualização

Data: Junho 2026
Agente usado: Claude Opus 4.6

---

## Fase atual

☑ Fase 1 — Local, terminal (Concluída)
☑ Fase 2 — Nuvem (Concluída — Neon + Cloudflare R2 + Render)
☑ Fase 3 — WhatsApp + LangGraph (Em andamento)
☐ Fase 4 — Web App

---

## Concluído

- [x] Configuração inicial do monorepo (pastas e arquivos básicos)
- [x] Criação da infraestrutura local (Docker Compose, requirements, .env)
- [x] Criação e conexão de banco de dados (`database.py`)
- [x] Inserção de dados via `seed.sql` com UUIDs corrigidos ('b...')
- [x] Criação do script de ingestão de PDFs (`ingestion_pdf.py`)
- [x] Testar a ingestão de um PDF real via linha de comando
- [x] Validar persistência e chunks no pgvector
- [x] Criar base da memória RAG e Agente (`memory.py` e `agent.py`)
- [x] Criar interface CLI (`chat.py`)
- [x] Criar pipeline de ingestão de áudio (`ingestion_audio.py`) com Whisper
- [x] Criar estruturação e persistência de checklists (`checklist.py`)
- [x] Desenvolver a Atualização de Perfil Automática (`profile.py`) e integrá-la aos fluxos de ingestão.
- [x] Configurar e validar o webhook do WhatsApp (Fase 3) para mensagens de texto.
- [x] Implementar recebimento e processamento de áudio via WhatsApp (Fase 3), incluindo roteamento de intenção (pergunta vs. checklist).
- [x] Migrar a transcrição de áudio de Whisper local para a API da OpenAI para melhorar performance e simplificar o ambiente.
- [x] Implementar histórico de conversa por usuário e ajustar temperature do LLM para maior precisão.

- [x] Adicionar nome do usuário ao prompt do sistema e usá-lo na saudação inicial do agente.
- [x] Implementar tom de voz contextualizado por perfil de usuário (família, admin, terapeuta) no prompt do sistema.
- [x] Injetar data e fuso horário atual no prompt do sistema para resolver referências temporais.
- [x] Substituir mensagens de erro genéricas por mensagens amigáveis e assinadas pelo agente Manolo.

- [x] Realizar consultas aos checklists via `chat.py` para validar recuperação
- [x] Refatorar a ingestão de mídia para um fluxo agnóstico de canal, centralizando a lógica em `ingestion_audio.py`.
- [x] Adicionar suporte à ingestão de PDFs no bot do Telegram com fluxo de conversa.
- [x] Integrar LangSmith para observabilidade e rastreamento das chamadas da OpenAI usando o decorador @traceable.

- [x] Implementar LangGraph como motor de orquestração do agente (`agent.py`) com MemorySaver.
- [x] Implementar extração silenciosa de checklist (PROMPT B4) — toda mensagem é analisada para dados de rotina.
- [x] Implementar cobrança conversacional de campos ausentes (uma pergunta por vez, linguagem natural).
- [x] Refatorar `checklist.py` para dados parciais (nunca sobrescrever com null) e função `buscar_campos_ausentes`.
- [x] Simplificar webhook `main.py` para delegar 100% ao grafo LangGraph.
- [x] Criar KB Denver ESDM em `core/kb/` (referência qualitativa para o Perfil Vivo).
- [x] Corrigir KeyError no roteamento condicional de arestas do LangGraph em `agent.py`.
- [x] Envelopar o cliente OpenAI compartilhado (`clients.py`) com `wrap_openai` para ativar traces finos da LLM no LangSmith.
- [x] Restaurar o feedback visual instantâneo "Consultando..." em background no webhook do WhatsApp.

---

## Decisões tomadas durante o desenvolvimento

> Registre aqui qualquer decisão que desviou do MANOLO.md ou que não estava prevista.
> Formato: data — decisão — motivo

| Data | Decisão | Motivo |
|---|---|---|
| Jun 2026 | Migração da transcrição de áudio de Whisper local para API da OpenAI | O modelo local (medium) estava lento e consumindo muitos recursos (CPU/RAM). A API oferece melhor performance e simplifica o ambiente Docker. |
| Jun 2026 | Criado bot de Telegram para teste rápido (`telegram_bot.py`) | Validar a experiência de interação via celular de forma imediata (Fase 1.5), evitando temporariamente a burocracia da Meta API (Fase 3). |
| Jun 2026 | **Telegram descontinuado** — foco 100% no WhatsApp | O bot Telegram (`telegram_bot.py`) era apenas para testes iniciais. A arquitetura segue focada no webhook do WhatsApp Business. O arquivo permanece no repositório mas não receberá atualizações. |
| Jun 2026 | LangGraph com MemorySaver (em memória) como MVP | Persistência de estado em RAM para velocidade de desenvolvimento. Migração para `langgraph-checkpoint-postgres` (Neon) será feita numa etapa posterior. |
| Jun 2026 | KB Denver como referência qualitativa, sem tabelas novas | Os inventários Denver ESDM (Níveis 1, 2, 3) são salvos como arquivos `.md` em `core/kb/`. Não criam tabelas no banco — o LLM os usa como contexto textual para enriquecer o Perfil Vivo e relatórios. |

---

## Problemas conhecidos / débitos técnicos

> Algo que funciona mas não está certo, ou que foi deixado para depois.
- **Configuração WhatsApp (Produção):** A implantação final com um número de telefone permanente ainda depende da resolução de um problema com a operadora. O desenvolvimento está funcional com o token de acesso temporário da Meta.
- **Persistência de Estado (LangGraph):** O MemorySaver atual é in-memory — um restart do Render limpa o estado das conversas (campo_pendente). Migrar para checkpoint no Neon futuramente.
- **Desalinhamento de Datas:** O formato de data no prompt (`DD/MM/YYYY`) difere do banco (`YYYY-MM-DD`). Documentado no `DEBITOS_TECNICOS.md`.
- **RAG Temporal:** Busca vetorial não filtra por data — retorna documentos antigos com igual prioridade. Documentado no `DEBITOS_TECNICOS.md`.

---

## Próximo passo
> 1. Testes em produção do novo motor LangGraph (extração Pydantic, empatia e guardrails) no WhatsApp Business.
> 2. Integração definitiva da KB Denver (`core/kb/`) no `profile.py` para enriquecer a terminologia clínica do Perfil Vivo.
> 3. **Evolução do Nó 6 (Cobrança):** Implementar RAG na KB Denver para que o LLM substitua as perguntas engessadas do dicionário por perguntas ativas de triagem clínica baseadas nos marcos de desenvolvimento do ESDM.
---

## Histórico de sessões

> Resumo rápido de cada sessão — o que foi feito.

| Data | Agente | O que foi feito |
|---|---|---|
| Jun 2026 | Gemini | Infraestrutura inicial, banco com pgvector, seed, script de ingestão de PDF, ingestão de áudio via Whisper, checklists, CLI de chat base e integração de teste via Telegram bot. |
| Jun 2026 | Gemini | Criação do `profile.py` para reescrita automática do Perfil Vivo em JSON via LLM, e integração com `ingestion_audio.py` e `ingestion_pdf.py`. |
| Jun 2026 | Gemini | Início da Fase 3: Criação do `main.py` (FastAPI) com rotas de verificação e escuta do webhook e `whatsapp.py` para disparo de respostas. Utilização de túnel via Pinggy. |
| Jun 2026 | Gemini | Validação e depuração do fluxo de ingestão de PDF com OCR. Corrigidos problemas de variáveis de ambiente e conexão com o banco de dados no ambiente Docker. |
| Jun 2026 | Gemini | Validação do fluxo de ingestão de áudio com Whisper e estruturação de checklist via LLM. |
| Jun 2026 | Gemini | Correção de bug no `telegram_bot.py` e refatoração da lógica de ingestão de mídia (`ingestion_audio.py`) para centralizar o processamento e simplificar os handlers de canais (ex: `telegram_bot.py`), preparando o código para reuso na integração com WhatsApp. |
| Jun 2026 | Gemini | Adicionado suporte à ingestão de PDFs no bot do Telegram, incluindo refatoração do `ingestion_pdf.py` e criação de um `ConversationHandler` para coletar metadados. |
| Jun 2026 | Gemini | Depuração completa do ambiente Docker e dos `imports` do Python. Configuração e validação do webhook do WhatsApp para o fluxo de chat de ponta a ponta. |
| Jun 2026 | Gemini | Implementação do fluxo de áudio no WhatsApp, com download, transcrição, roteamento de intenção (pergunta/checklist) e notificações de sucesso/erro. |
| Jun 2026 | Gemini | Implementação de histórico de conversa no agente e ajuste da temperatura do LLM para 0.2. Atualização das chamadas do agente nos canais (CLI, WhatsApp, Telegram) para incluir o identificador do usuário. |
| Jun 2026 | Gemini | Reversão da funcionalidade de indicador "digitando" no WhatsApp. A API da Meta não suporta esta ação, causando erros. O código foi limpo para remover a complexidade desnecessária. |
| Jun 2026 | Gemini | Correção de bug no webhook do WhatsApp (KeyError por conta do RealDictCursor). Mapeamento das inconsistências de roteamento, datas e volatilidade do histórico no arquivo DEBITOS_TECNICOS.md. |
| Jun 2026 | Gemini | Integração do LangSmith para observabilidade de chamadas da OpenAI utilizando o decorador @traceable nos módulos de agente e pipelines de ingestão. |
| Jun 2026 | Claude Opus 4.6 / Gemini | Implementação do LangGraph como motor de orquestração (6 nós, MemorySaver, PROMPT B4, dados parciais, simplificação do webhook, KB Denver). Resolução de KeyError no roteador, reintrodução de feedback "Consultando..." e integração de traces detalhados de LLM via wrap_openai. |
| Jun 2026 | Gemini 3.1 Pro | Refatoração completa da extração (Structured Outputs via Pydantic), mapeamento direto em colunas SQL no `checklist.py` ao invés de dumps JSON, conversão de datas para o padrão brasileiro nas respostas, adição de **empatia** aos nós de confirmação de checklist com integração orgânica de perguntas, e implementação de **guardrails de escopo e clínico** (prevenção de diagnósticos médicos). |
