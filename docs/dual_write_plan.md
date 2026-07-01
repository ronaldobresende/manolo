# Plano de Implementação Futura: Arquitetura Dual-Write (Acumulativo + Eventos)

## Objetivo
Implementar uma arquitetura de escrita dupla (Dual-Write) onde o sistema extrai, a partir de uma única mensagem, tanto o resumo consolidado do dia (modelo acumulativo, ideal para o LLM gerar respostas fluidas e manter contexto comportamental) quanto a lista cronológica de eventos (ideal para painéis analíticos e dashboards da Fase 4).

## 1. Banco de Dados (`scripts/events.sql` e `core/database.py`)
- **Novas Tabelas (Eventos):**
  - `checklist_alimentacao_eventos`
  - `checklist_comunicacao_eventos`
  - `checklist_sono_eventos`
  - `checklist_tela_eventos` (campos: `horario_inicio`, `horario_fim`, `conteudo`, `dispositivo`)
- **Tabelas Atuais (Acumulativas):**
  - **NÃO dropar** as tabelas atuais. Elas serão mantidas e continuarão servindo como base principal de RAG para o bot.

## 2. Schemas do LLM (`core/schemas.py`)
- Criar os novos modelos Pydantic focados nos eventos: `AlimentacaoEventoModel`, `ComunicacaoEventoModel`, `SonoEventoModel` e `TelaEventoModel`.
- Expandir o objeto principal `CamposPreenchidos` para que ele contenha as duas vias:
  - Campos normais acumulativos: `alimentacao`, `tela`, `sono`, etc.
  - Campos de eventos (listas): `eventos_alimentacao`, `eventos_tela`, `eventos_sono`, `eventos_comunicacao`.

## 3. Orquestrador e Prompt (`agent/agent.py`)
- Adicionar uma regra clara no `prompt_extracao` orientando o LLM: *"Para as categorias de alimentação, comunicação, sono e tela, gere TANTO o resumo acumulativo global QUANTO a lista cronológica exata de eventos separados nos arrays de eventos correspondentes."*

## 4. Persistência de Dados (`agent/checklist.py`)
- A função `_upsert_campos_no_banco` deve ser expandida.
- O fluxo de `UPSERT` atual para as tabelas acumulativas (usando `COALESCE`, `array_cat`, `CONCAT_WS`) **permanece intacto**.
- **Adição:** Se o JSON retornado contiver os arrays de eventos (ex: `eventos_alimentacao`), o backend fará um laço `for` e executará um `INSERT INTO` simples nas respectivas tabelas de eventos atrelando-os ao `checklist_id` vigente.
