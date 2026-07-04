# Tarefas de IA do Sistema Manolo

Este documento descreve detalhadamente cada tarefa onde a Inteligência Artificial é acionada no sistema Manolo, com o seu respectivo fluxo de negócio, entrada/saída e qual modelo está sendo utilizado na versão atual do código. 

Use este documento como contexto ao interagir com LLMs (Claude, GPT, Gemini) para pedir recomendações de quais modelos seriam os mais adequados (melhor custo-benefício, performance, inteligência) para cada etapa da nossa refatoração.

---

## 1. Roteamento de Intenção (Classificação Rápida)
* **Modelos Atuais**: `gpt-4o-mini` (texto via LangGraph em `agent.py`) e `gpt-4o` (áudio via `ingestion_audio.py`)
* **Descrição da Tarefa**: 
O sistema recebe a primeira mensagem ou transcrição de áudio enviada pelos pais no WhatsApp e precisa classificar a intenção em categorias predefinidas (ex: `checklist` para relato de rotina, `pergunta` para consultas de histórico, `relatorio_checklist` para resumos do dia).
* **Contexto Técnico**: Exige baixíssima latência (rápido), baixo custo (rodado a cada mensagem) e responde de forma exata com uma única palavra pré-definida.

## 2. Extração Estruturada (Checklist Silencioso)
* **Modelos Atuais**: `gpt-4o-mini` (texto via LangGraph) e `gpt-4o` (áudio)
* **Descrição da Tarefa**: 
Lê o relato dos pais sobre o dia da criança e extrai as informações encaixando-as de forma perfeita em um JSON Schema rigoroso (via Pydantic). O JSON mapeia dezenas de colunas do banco de dados relacional (sono, alimentação, brincar, tela, banheiro, humor e terapias).
* **Contexto Técnico**: Precisa de altíssima confiabilidade e suporte nativo robusto a **Structured Outputs**. Pode ler relatos longos com ambiguidades e deve evitar "alucinar" preenchendo campos de forma mentirosa caso os pais não os tenham mencionado.

## 3. RAG / Consulta Livre (Agente Conversacional)
* **Modelo Atual**: `gpt-4o`
* **Descrição da Tarefa**: 
Atua como o "cérebro amigável" do Manolo. Quando os pais fazem perguntas ("a fono sugeriu alguma atividade para o desfralde?", "como ele dormiu na última terça?"), o sistema junta os eventos diários recentes + recortes semânticos de laudos médicos passados e envia ao LLM.
* **Contexto Técnico**: Exige excelente capacidade analítica e de raciocínio temporal (relacionar "ontem" ou "semana passada" às datas corretas). Demanda **extrema empatia e tom de voz acolhedor**. O modelo deve obedecer estritamente a *guardrails* para NUNCA dar diagnósticos médicos.

## 4. Geração de Relatórios e Resumos
* **Modelos Atuais**: `gpt-4o-mini` (para inferir datas) e `gpt-4o` (para escrever o parágrafo humanizado)
* **Descrição da Tarefa**: 
Se o pai pede um resumo do dia, o sistema (1) aciona um LLM muito rápido apenas para inferir que "data" o pai quis dizer com a mensagem, e (2) resgata o JSON bruto do banco e passa para outro LLM redigir uma "historinha" calorosa resumindo como foi a rotina da criança hoje, repassando o resultado ao usuário.
* **Contexto Técnico**: Necessita da combinação de modelo barato (para roteamento/extração de datas YYYY-MM-DD em milissegundos) e um modelo excelente em redação humanizada para não soar robótico.

## 5. Síntese do Perfil Vivo (Memória Contínua)
* **Modelo Atual**: `gpt-4o`
* **Descrição da Tarefa**: 
O "Perfil Vivo" é um JSON orgânico com características atemporais da criança (ex: palavras que fala, o que o irrita). Após a inserção de novos laudos ou checklists diários, esse nó pega o Perfil Atual + os dados dos últimos 30 dias e reescreve todo o perfil, cruzando informações, notando o que melhorou e o que estagnou.
* **Contexto Técnico**: A tarefa de maior exigência analítica do projeto. Requer uma janela de contexto gigantesca (*Long Context*) para ler dezenas de páginas de laudos cruzados com checklists sem esquecer/omitir nuances vitais do diagnóstico.

## 6. Extração OCR em PDFs (Laudos Médicos)
* **Modelo Atual**: `gpt-3.5-turbo`
* **Descrição da Tarefa**: 
Ao se fazer o upload de PDFs brutos de terapias ou diagnósticos (às vezes contendo textos de OCR sujos/mal diagramados), o modelo deve varrer a primeira página para extrair apenas: a data do laudo, a categoria do documento e a especialidade do emissor (ex: neurologista, psicólogo).
* **Contexto Técnico**: Tarefa extrativista e rápida. Exige um modelo barato com boa capacidade de lidar com blocos de texto truncados vindos de PDF.

## 7. Transcrição de Áudio e Criação de Vetores
* **Modelos Atuais**: `whisper-1` (transcrição) e `text-embedding-3-small` (vetorização)
* **Descrição da Tarefa**: 
Transformar os áudios do WhatsApp (frequentemente contendo choro de criança ou barulhos de pratos de fundo) em texto cru, e transformar os PDFs textuais em arrays matemáticos de 1536 dimensões para serem salvos no banco PostgreSQL com extensão `pgvector`.

## 8. Scripts de Limpeza/Backfill de Banco de Dados
* **Modelo Atual**: `gpt-4o-mini` (ex: `backfill_cochilos.py`)
* **Descrição da Tarefa**: 
Sempre que uma nova coluna no banco é criada (ex: `cochilo_inicio`), rodam-se scripts para pegar as anotações textuais antigas salvas e extrair de lá as horas/booleanos para popular essa nova coluna de forma estruturada.
* **Contexto Técnico**: Trabalho em *batch* (lote) com milhares de linhas e baixo custo mandatório.
