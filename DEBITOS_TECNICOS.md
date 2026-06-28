# Débitos Técnicos Identificados

Este documento registra as inconsistências de comportamento e problemas arquiteturais detectados a partir dos logs de interações reais do bot do WhatsApp em Junho/2026.

---

## 1. Roteamento de Mensagens de Texto (Falta de Classificação) — [RESOLVIDO]
* **O Problema:** No webhook anterior do WhatsApp, apenas as mensagens do tipo `audio` passavam pelo classificador de intenção. Mensagens de texto iam direto para pergunta livre, fazendo com que relatos de rotina escritos não fossem salvos nos checklists.
* **Resolução:** Resolvido na Fase 3 com a introdução do LangGraph. Agora, o nó de `extrair_checklist_silencioso` processa todas as mensagens de entrada (tanto texto quanto áudio transcrito) antes da classificação de intenção principal. O nó de classificação analisa a intenção de todas as mensagens unificadamente.

---

## 2. Volatilidade do Histórico de Conversa (`conversation_history`) — [RESOLVIDO]
* **O Problema:** O histórico de conversa (`conversation_history`) era um dicionário global em RAM. Qualquer reinicialização do Render limpava o histórico e usuários diferentes tinham contextos isolados de chat, impedindo o compartilhamento de informações recentes.
* **Resolução:** Resolvido utilizando o `MemorySaver` do LangGraph configurado por `thread_id` (telefone do usuário). O estado de conversação agora é gerenciado pelo grafo. Além disso, como o RAG busca diretamente no Neon e a extração silenciosa persiste no banco, a informação relatada por um usuário (ex: Denise) fica imediatamente disponível para a busca de outro usuário (ex: Ronaldo) através do Neon, sem depender da RAM de instâncias específicas.

---

## 3. Inconsistência no Formato de Datas (Desvio Temporal)
* **O Problema:** A data e a hora atual inseridas no prompt de sistema pelo `agent.py` utilizam o formato brasileiro `DD/MM/YYYY` (ex: `27/06/2026`). No entanto, os registros de checklists no banco de dados e as respostas retornadas pelo RAG formatam a data no padrão SQL `YYYY-MM-DD` (ex: `--- Dia 2026-06-27 ---`).
* **Impacto:** O LLM (como o `gpt-4o`) precisa traduzir mentalmente as datas. Embora inteligente, o modelo pode falhar em correlacionar que a data do prompt é o "hoje" dos checklists se o fuso horário ou a formatação causarem confusão, gerando respostas em que ele afirma não ter o checklist de "hoje" mesmo quando há um checklist datado com a data correspondente.
* **Solução:** Padronizar todas as exibições de data no prompt do agente para usar o mesmo padrão (de preferência o descritivo ou ambos formatos correlacionados de forma clara).

---

## 4. RAG sem Contexto Temporal em Documentos
* **O Problema:** A busca vetorial por similaridade (`buscar_contexto_documentos`) em chunks de laudos e relatórios não leva em conta a data de criação do documento.
* **Impacto:** Se o usuário perguntar *"O que o Bernardo comeu hoje?"* ou *"Como foi a fono de hoje?"*, a busca semântica pode trazer trechos de documentos antigos de 6 meses atrás porque contêm a palavra "hoje" ou "alimentação". O LLM, ao ler *"Trecho Documento: Hoje o Bernardo comeu..."*, pode responder como se isso estivesse acontecendo na data atual.
* **Solução:** Modificar a tabela de `documento_chunks` ou a consulta RAG para sempre retornar e exibir a data de criação do documento como metadado explícito no prompt do LLM (ex: `--- Trecho de Laudo Fonoaudiológico de 10/12/2025 ---`).

