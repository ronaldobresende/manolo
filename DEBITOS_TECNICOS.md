# Débitos Técnicos Identificados

Este documento registra as inconsistências de comportamento e problemas arquiteturais detectados a partir dos logs de interações reais do bot do WhatsApp em Junho/2026.

---

## 1. Roteamento de Mensagens de Texto (Falta de Classificação)
* **O Problema:** No webhook do WhatsApp (`channels/main.py`), apenas as mensagens do tipo `audio` passam pelo classificador de intenção (`_determinar_intencao_audio`) para decidir se são perguntas ou relatos de checklist. As mensagens de tipo `text` vão direto para a função `processar_e_enviar_resposta` (fluxo de pergunta livre).
* **Impacto:** Se o usuário relatar o dia do Bernardo por escrito (ex: *"Hoje ele comeu bem, mamou às 9h, dormiu às 22h"*), os dados não serão estruturados nem salvos nas tabelas relacionais de checklist. A informação ficará presa apenas no histórico temporário de chat.
* **Solução:** Passar a mensagem de texto pelo classificador de intenção se ela contiver termos relacionados à rotina ou caso ela não seja estruturada como uma pergunta explícita, roteando para a estruturação de checklist quando aplicável.

---

## 2. Volatilidade do Histórico de Conversa (`conversation_history`)
* **O Problema:** O dicionário `conversation_history` que mantém o contexto de conversa do usuário é global e fica em memória no arquivo `agent/agent.py`.
* **Impacto:** 
  1. Qualquer reinicialização, build ou deploy do servidor no Render apaga completamente o histórico.
  2. Caso haja escala horizontal para múltiplas instâncias, o histórico não será compartilhado.
  3. Usuários diferentes conversando paralelamente possuem contextos isolados e não compartilham informações recentes a menos que estas já estejam no banco (o que explica o Ronaldo não saber o que o Bernardo comeu, uma vez que a Denise enviou por texto e ficou apenas no histórico de conversa dela).
* **Solução:** Criar uma tabela simples `historico_conversas` no banco Postgres (Neon) e buscar/adicionar mensagens de chat com base no `telefone_whatsapp` ou `usuario_id` a cada interação.

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
