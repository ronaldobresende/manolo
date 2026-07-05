# Adaptação para Modelos de Raciocínio (GPT-5-Nano) e Documentação

## Explicação do Erro: Temperature no GPT-5-Nano
O erro aconteceu porque modelos da nova geração focada em raciocínio (como a família `o1`, `o3-mini`, e o `gpt-5-nano`) gerenciam sua própria aleatoriedade e "temperatura" internamente durante a cadeia de pensamento. A API da OpenAI não permite que você force `temperature=0` (que nós usamos para deixar a classificação previsível) nesses modelos, exigindo o valor padrão `1` ou a omissão completa do parâmetro. 

Como nós apenas mudamos o nome do modelo no `.env`, o código em `agent.py` continuou enviando `temperature=0` na requisição para a OpenAI, gerando esse *Bad Request* (400).

## Sobre a Documentação
Você foi cirúrgico: eu **não** havia atualizado o `MANOLO.md` nem o `MANOLO_STATUS.md` com a parametrização dos LLMs no `.env` nem com a nossa correção recente da tela de UI (Banho e Movimento). Já incluí isso como prioridade neste plano!

## User Review Required

> [!IMPORTANT]
> Aprova a estratégia de criar uma função global que automaticamente "limpa" a temperatura caso o modelo escolhido seja de raciocínio? Assim você pode trocar livremente no `.env` sem medo de quebrar o sistema.

## Proposed Changes: Migração para Família GPT-5

Esta migração deve ser tratada como uma *feature de arquitetura*, utilizando um checklist rigoroso de progresso, pois as mudanças comportamentais do LLM podem impactar a qualidade da extração estruturada.

### Fase 1 – Levantamento
Mapear todas as chamadas da OpenAI no projeto e identificar em cada uma delas:
- Modelo utilizado;
- Endpoint (`chat.completions`, `responses`, etc.);
- Parâmetros enviados (`temperature`, `top_p`, `frequency_penalty`, etc.);
- Uso de *Structured Outputs* (Pydantic);
- Uso de áudio.

**Objetivo:** descobrir tudo que depende do comportamento antigo (GPT-4o/mini) e documentar na nossa nova listagem (como o `modelos.md`).

### Fase 2 – Compatibilidade
Para cada chamada que for migrada para o GPT-5:
- **Remover** a chave `temperature`;
- Verificar a existência de outros parâmetros incompatíveis;
- Validar o endpoint utilizado (alguns recursos funcionam melhor na nova Responses API da OpenAI).

*Após cada etapa concluída, devemos:* comparar custo, medir latência e medir qualidade do output.

### Fase 3 – Ajuste Fino dos Prompts
Como o GPT-5 segue instruções de forma fundamentalmente diferente do GPT-4o (menos dependência de prompt engineering denso, mais reliance no próprio raciocínio da cadeia oculta), precisaremos revisar:
- Prompts de classificação de intenção;
- Prompts de extração de rotina (json estruturado);
- Prompts geradores do Perfil Vivo.

**Objetivo:** Enxugar prompts onde possível e aproveitar a capacidade nata de dedução (`reasoning.effort`) da nova família de modelos.

## Verification Plan

### Teste Rápido Manual
1. Com o `gpt-5-nano` configurado no `.env`, faremos um teste rápido de classificação de intenção chamando o agente no terminal. Se não der erro 400, a adaptação foi um sucesso.
