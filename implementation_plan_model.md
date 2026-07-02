# [Implementação: Centralização de Modelos (Preparação Multimodelo / Gemini)]

Você tem absoluta razão. Como fomos desenvolvendo iterativamente, os nomes dos modelos (como `gpt-4o` e `gpt-4o-mini`) acabaram ficando "chumbados" (hardcoded) direto no meio da lógica de dezenas de arquivos. Se hoje quisermos virar a chave para o Gemini 1.5 Pro, seria um inferno de "Localizar e Substituir".

Esse plano resolve essa bagunça arquitetural centralizando tudo.

## Proposed Changes

Vamos criar variáveis globais de ambiente no `config.py` e `.env` com uma **arquitetura granular por tarefa**. Para cada nó do nosso sistema, você poderá configurar o modelo exato e a temperatura.

**1. Roteamento (Intenção)**:
- `LLM_MODEL_ROUTING` (Recomendado: `gemini-1.5-flash` ou `gpt-4o-mini`)
- *Por que:* A tarefa de decidir se é "dúvida" ou "relato" exige milissegundos e custo próximo a zero. O Flash e o Mini dominam essa categoria.

**2. Extração de Checklists (Áudio/Texto)**:
- `LLM_MODEL_EXTRACTION` (Recomendado: `gpt-4o`)
- *Por que:* Para forçar o LLM a cuspir um JSON complexo sem pular campos (Structured Outputs), a OpenAI ainda possui a API mais rígida e determinística do mercado, garantindo zero falhas de parsing no banco de dados.

**3. RAG e Conversa Livre**:
- `LLM_MODEL_RAG` (Recomendado: `claude-3-5-sonnet-20240620`)
- *Por que:* O Claude 3.5 Sonnet é indiscutivelmente o modelo com a linguagem mais natural, empática e menos robótica. Para responder aos pais sobre o desenvolvimento do filho, ele é o único que não soa como "um assistente de IA".

**4. Síntese de Perfil Vivo**:
- `LLM_MODEL_PROFILE` (Recomendado: `gemini-1.5-pro`)
- *Por que:* Ele tem a melhor capacidade de janela de contexto do mundo (até 2 milhões de tokens). Para ler 90 dias de laudos em PDF e cruzar com checklists sem ter "amnésia", ele é o rei da análise profunda.

**5. Análise e Validação de PDFs**:
- `LLM_MODEL_PDF` (Recomendado: `gpt-4o-mini` ou `claude-3-5-haiku`)
- *Por que:* São os melhores modelos de baixo custo com capacidades visuais excelentes para varrer um PDF rápido e extrair texto.

**6. Modelos Auxiliares (Não-Texto)**:
- `AUDIO_TRANSCRIPTION_MODEL` (Padrão: `whisper-1`)
- `EMBEDDING_MODEL` (Padrão: `text-embedding-3-small`)

### 2. Limpeza do Código (Substituição)
Em todos os arquivos que instanciam o LLM, vamos importar `settings` e trocar a string fixa pela variável.

#### [MODIFY] [agent.py](file:///c:/projects/python/manolo/agent/agent.py)
- Em `classificar_intencao`, `processar_transcricao`, `rag_node`, `gerar_relatorio_checklist_node` (x5 instâncias).

#### [MODIFY] [profile.py](file:///c:/projects/python/manolo/agent/profile.py)
- Em `atualizar_perfil` (x1 instância).

#### [MODIFY] [audio_processor.py](file:///c:/projects/python/manolo/ingestion/audio_processor.py) e [ingestion_audio.py](file:///c:/projects/python/manolo/ingestion/ingestion_audio.py)
- Na transcrição e análise dos áudios (x3 instâncias).

#### [MODIFY] [pdf_processor.py](file:///c:/projects/python/manolo/ingestion/pdf_processor.py) e [ingestion_pdf.py](file:///c:/projects/python/manolo/ingestion/ingestion_pdf.py)
- No classificador de OCR e documentos (x2 instâncias).

### 3. Preparando o Terreno para o Gemini (Dica)
> [!TIP]
> A beleza dessa centralização é que **a API do Gemini do Google é 100% compatível com a biblioteca da OpenAI**. 
> Quando você quiser testar o Gemini, nós só precisaremos adicionar `LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"` no seu `.env` e trocar o `LLM_MODEL_DEFAULT="gemini-1.5-pro"`. O Manolo inteiro vai virar Gemini em 2 segundos sem você reescrever nenhuma linha de código de Pydantic/Structured Outputs!

## Verification Plan
1. Após a refatoração, faremos uma busca por texto puro (`gpt-4`) na base de código para garantir que zeramos as instâncias chumbadas.
2. Testaremos uma requisição simples na CLI (`chat.py`) para confirmar que a injeção da variável `settings.LLM_MODEL_DEFAULT` está funcionando na API.
