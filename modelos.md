# Guia de Migração: Modelos (GPT-4o para Família GPT-5)

### 1. Roteamento de intenção (`agent.py`)
- **Atual:** `gpt-4o-mini`
- **Novo:** `gpt-5-nano` *(Reasoning: `low`)*
- **Observação:** Classificação simples

### 1b. Roteamento via áudio (`ingestion_audio.py`)
- **Atual:** `gpt-4o`
- **Novo:** `gpt-5-nano` *(Reasoning: `low`)*
- **Observação:** Após transcrição

### 2. Checklist estruturado (JSON/Pydantic)
- **Atual:** `gpt-4o-mini`
- **Novo:** `gpt-5-mini` *(Reasoning: `medium`)*
- **Observação:** Melhor structured outputs

### 2b. Checklist vindo de áudio
- **Atual:** `gpt-4o`
- **Novo:** `gpt-5-mini` *(Reasoning: `medium`)*
- **Observação:** Mesmo motivo acima

### 3. RAG / agente conversacional
- **Atual:** `gpt-4o`
- **Novo:** `gpt-5` *(Reasoning: `medium`)*
- **Observação:** Melhor reasoning temporal

### 4a. Inferência de data do relatório
- **Atual:** `gpt-4o-mini`
- **Novo:** `gpt-5-nano` *(Reasoning: `low`)*
- **Observação:** Parsing de data

### 4b. Escrita do resumo humanizado
- **Atual:** `gpt-4o`
- **Novo:** `gpt-5` *(Reasoning: `low`)*
- **Observação:** Writing / empathy

### 5. Perfil Vivo
- **Atual:** `gpt-4o`
- **Novo:** `gpt-5` *(Reasoning: **`high`**)*
- **Observação:** Principal workload de reasoning

### 6. OCR de laudos PDF
- **Atual:** `gpt-3.5-turbo`
- **Novo:** `gpt-5-nano` *(Reasoning: `low`)*
- **Observação:** Extraction barata

### 7. Transcrição
- **Atual:** `whisper-1`
- **Novo:** **manter**
- **Observação:** Continua bom

### 7b. Embeddings
- **Atual:** `text-embedding-3-small`
- **Novo:** **manter**
- **Observação:** Continua bom

### 8. Backfill scripts
- **Atual:** `gpt-4o-mini`
- **Novo:** `gpt-5-nano` *(Reasoning: `low`)*
- **Observação:** Batch barato
