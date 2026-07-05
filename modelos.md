| Onde / Tarefa                                   | Atual no código          | Novo (modelo) | Reasoning | Observação                      |
| ----------------------------------------------- | ------------------------ | ------------- | --------- | ------------------------------- |
| 1. Roteamento de intenção (`agent.py`)          | `gpt-4o-mini`            | `gpt-5-nano`  | `low`     | Classificação simples           |
| 1b. Roteamento via áudio (`ingestion_audio.py`) | `gpt-4o`                 | `gpt-5-nano`  | `low`     | Após transcrição                |
| 2. Checklist estruturado (JSON/Pydantic)        | `gpt-4o-mini`            | `gpt-5-mini`  | `medium`  | Melhor structured outputs       |
| 2b. Checklist vindo de áudio                    | `gpt-4o`                 | `gpt-5-mini`  | `medium`  | Mesmo motivo acima              |
| 3. RAG / agente conversacional                  | `gpt-4o`                 | `gpt-5`       | `medium`  | Melhor reasoning temporal       |
| 4a. Inferência de data do relatório             | `gpt-4o-mini`            | `gpt-5-nano`  | `low`     | Parsing de data                 |
| 4b. Escrita do resumo humanizado                | `gpt-4o`                 | `gpt-5`       | `low`     | Writing / empathy               |
| 5. Perfil Vivo                                  | `gpt-4o`                 | `gpt-5`       | **high**  | Principal workload de reasoning |
| 6. OCR de laudos PDF                            | `gpt-3.5-turbo`          | `gpt-5-nano`  | `low`     | Extraction barata               |
| 7. Transcrição                                  | `whisper-1`              | **manter**    | —         | Continua bom                    |
| 7b. Embeddings                                  | `text-embedding-3-small` | **manter**    | —         | Continua bom                    |
| 8. Backfill scripts                             | `gpt-4o-mini`            | `gpt-5-nano`  | `low`     | Batch barato                    |
