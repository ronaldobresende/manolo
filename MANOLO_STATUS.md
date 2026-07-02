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
☑ Fase 4 — Web App (MVP e Autenticação Concluídos)

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

**Fase 4 (Web App):**
- [x] Estruturação do Next.js (App Router), Tailwind CSS e TypeScript em `web/`.
- [x] Criação de layout responsivo com Sidebar e Header.
- [x] Criação do Dashboard (Perfil Vivo, Marcos Recentes).
- [x] Gráficos de evolução (Sono, Humor, Comunicação, Brincar) usando Recharts.
- [x] Visualização detalhada e tabulada dos Checklists Diários.
- [x] Tela de Documentos com suporte a upload de PDFs via FastAPI para R2.
- [x] Implementação da API REST (Backend FastAPI) `channels/api.py`.
- [x] **Fase 4.1 (Segurança):** Implementação de JWT via cookies (`middleware.ts`, `app/actions.ts` e `core/security.py`), scripts de senha e validação de sessão protegendo `/dashboard/*`.

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
| Jun 2026 | Alteração do comportamento do banco para UPSERT com acúmulo dinâmico | Inicialmente definido como `DO NOTHING` para evitar deleções acidentais pelo LLM. Modificado para `ON CONFLICT DO UPDATE` com concatenação de arrays (`array_cat`) e `COALESCE` para permitir acúmulo natural de múltiplos relatos curtos enviados em momentos diferentes do dia, sem perda de dados históricos. |

---

## Problemas conhecidos / débitos técnicos

> Algo que funciona mas não está certo, ou que foi deixado para depois.
- **Configuração WhatsApp (Produção):** A implantação final com um número de telefone permanente ainda depende da resolução de um problema com a operadora. O desenvolvimento está funcional com o token de acesso temporário da Meta.
- **Persistência de Estado (LangGraph):** O MemorySaver atual é in-memory — um restart do Render limpa o histórico de `data_contexto`. Migrar para checkpoint no Neon futuramente.
- **RAG Temporal:** Busca vetorial não filtra por data — retorna documentos antigos com igual prioridade. Documentado no `DEBITOS_TECNICOS.md`.

---

## Próximo passo
> 1. Testes em produção do grafo simplificado (extração silenciosa, relatório sob demanda, sem cobranças) no WhatsApp Business.
> 2. Integração definitiva da KB Denver (`core/kb/`) no `profile.py` para enriquecer a terminologia clínica do Perfil Vivo.
> 3. **Migração do MemorySaver** para checkpoint persistente no Neon (`langgraph-checkpoint-postgres`) para não perder `data_contexto` a cada restart.
> 4. **Evolução para Agentic RAG**: Dar autonomia ao nó de RAG usando "Tool Calling" (`bind_tools`) para que o LLM escolha quais dados e janelas de tempo consultar no banco de dados, em vez do SQL fixo atual de 15 dias.
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
| Jun 2026 | Gemini 3.1 Pro | Refatoração completa da extração (Structured Outputs via Pydantic), mapeamento direto em colunas SQL, conversão de datas (BR), **empatia orgânica**, e **guardrails de escopo e clínico**. \n\n**Atualização Crítica de Arquitetura (Amnésia de Data):** Refatoração do Schema para suportar extração de múltiplos dias em uma única mensagem (`List[RelatoDiario]`). Implementada ancoragem de contexto temporal (`data_contexto` na state do LangGraph), bloqueio de alucinação no RAG (separação estrita de Perfil Vivo e Eventos Diários), confirmação leve para datas implícitas/ambíguas, cálculo de dias da semana (ex: 'quarta passada') por LLM, e função SQL `mesclar_checklists` para Correção Retroativa de Datas (Ctrl+Z invisível). |
| Jun 2026 | Gemini 3.1 Pro | Implementação da **Fase 4 e 4.1 (Web App e Autenticação)**. Criação completa do frontend Next.js com dashboards e gráficos (Recharts). Backend estendido com rotas REST e sistema de segurança (JWT com bcrypt), Server Actions no frontend e Next.js Middleware para roteamento privado. |
| Jun 2026 | Gemini 3.1 Pro | **Simplificação Radical do LangGraph (Pragmatismo & Segurança):** Removidos os nós proativos de cobrança de pendências (Nós 5 e 6). Grafo reordenado para iniciar na `classificar_intencao`, roteando para Extração Silenciosa ou RAG. `salvar_campo_individual` alterado para `DO NOTHING` (nunca sobrescrever, resolvendo o bug de deleção de dados acidental). Implementado Nó de Relatório Sob Demanda para retornar um resumo formatado (`formatar_resumo_diario`) com link para o Web App. |
| Jun 2026 | Gemini 3.1 Pro | **Refinamento do Web App e Infraestrutura:** Correção de bugs de UI/UX críticos no `TagInput` (crash de tela e delimitador por vírgula) que impediam carregamento dos checklists de Comunicação e Brincar. Ajuste na interface do menu lateral para suportar o carregamento nativo de `logo.png`. Orientação e documentação para credenciais Cloudflare R2 corrigindo falhas de upload de fotos de perfil. Ampliação do Dashboard de Evolução, com gráficos detalhados de Horário de Dormir (com meta dinâmica invertida) e Tempo de Tela (convertido para HH:MM). Refatoração completa da formatação da string de resumo do robô no WhatsApp, entregando relatórios super descritivos ao invés de booleanos simples. |
| Jun 2026 | Claude Sonnet 4.6 / Gemini 3.1 Pro | **Correção de 3 Bugs Críticos no RAG e Relatórios (identificados em logs de produção):** (1) **RAG cego para checklists** — `buscar_contexto_checklists` em `memory.py` reescrita com JOIN completo nas 10 tabelas filhas (alimentação, brincar, tela, comunicação, higiene, vestuario, movimento, rotina, observações); antes só 3 tabelas eram consultadas, tornando 70% dos dados invisíveis ao RAG. (2) **Alucinação Perfil Vivo vs. Eventos** — adicionado guardrail explícito no `prompt_usuario` do nó RAG impedindo o LLM de substituir dados reais ausentes pelas preferências genéricas do Perfil Vivo. (3) **Relatório ignorava a data pedida** — `gerar_relatorio_checklist_node` em `agent.py` agora extrai a data diretamente da mensagem (regex DD/MM/YYYY e YYYY-MM-DD) antes de consultar o banco. |
| Jun 2026 | Gemini 3.1 Pro | **Acúmulo Diário de Relatos (UPSERT):** Corrigido bug de perda de dados ao enviar mensagens fragmentadas ao longo do dia. O banco não usa mais `DO NOTHING`. Refatoração para usar `ON CONFLICT DO UPDATE` em 10 tabelas com suporte a concatenação de arrays do Postgres (`array_cat`) e `COALESCE`, permitindo acumular múltiplos relatos no mesmo dia (ex: adicionando itens sucessivos em `aceitou` sem apagar os anteriores). Ajustada resposta silenciosa para retornar `"Anotado! ✅"` a fim de evitar erro 400 da Meta API com corpo vazio, mas mantendo a estratégia do grafo simples. |
