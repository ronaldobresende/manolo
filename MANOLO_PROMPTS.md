# MANOLO — Prompts de Features para o Gemini

> Execute um prompt por vez. Aguarde o Gemini entregar e revise antes de passar para o próximo.
> Marque como concluído conforme for implementando.

---

## Filosofia do Checklist

O checklist **não deve ser preenchido — deve ser extraído.**

O usuário vive o dia e registra naturalmente em conversas pelo WhatsApp/Telegram.
O Manolo escuta, interpreta e estrutura silenciosamente no banco.

```
Usuário (14h): "Bernardo almoçou bem, comeu arroz e frango, usou a colher!"
Manolo: registra checklist_alimentacao + checklist_comunicacao silenciosamente

Usuário (21h): "Teve uma crise quando tirou o tablet, se acalmou com música"
Manolo: registra checklist_humor + checklist_tela silenciosamente
```

Ao final do dia o checklist está 70% preenchido sem nenhum formulário.

**O Manolo só cobra ativamente o que não conseguiu inferir — e de forma conversacional:**
> "Boa noite! Como foi o sono do Bernardo ontem à noite?"

Uma pergunta. Uma resposta. Nunca um formulário.

**Regra para todos os prompts de checklist:**
- Nunca listar "campos faltantes" de forma burocrática
- Sempre perguntar de forma natural sobre UMA coisa por vez
- Extrair dados de qualquer mensagem espontânea do usuário
- O Bernardo tem 2 anos e 6 meses — a rotina é caótica, o sistema deve se adaptar à família, não o contrário

---

## 🔴 Alta Prioridade

---

### PROMPT A1 — Resumo Semanal Automático

```
Analise o projeto Manolo (leia MANOLO.md para contexto).

Implemente um resumo semanal automático com as seguintes regras:

1. GATILHO
Em channels/main.py (ou telegram_bot.py), quando o usuário
mandar a primeira mensagem de uma segunda-feira, verificar
se já foi enviado o resumo semanal hoje.
Controle via dicionário em memória:
resumo_enviado[telefone] = date.today()

O controle é individual por telefone — pai e mãe recebem
o resumo separadamente, cada um na sua primeira interação
da segunda-feira. Não compartilhar o controle entre usuários.

2. GERAÇÃO DO RESUMO
Criar função gerar_resumo_semanal(crianca_id) em agent/agent.py.
Buscar checklists dos últimos 7 dias no banco.
Enviar para o LLM com prompt:
"Analise os registros da semana passada e gere um resumo
caloroso e encorajador para a família, destacando:
- Padrões de sono
- Evolução na alimentação
- Destaques de comunicação
- Conquistas ou momentos especiais
- Algo que pode merecer atenção
Seja específico com números quando possível.
Termine com uma frase de encorajamento.
Responda em português."

3. FORMATO DA MENSAGEM
Prefixo: "📊 Resumo da semana de {data_inicio} a {data_fim} — Bernardo\n\n"
Seguido pelo texto gerado pelo LLM.

4. FALLBACK
Se não houver checklists suficientes (menos de 3 dias):
"Ainda não temos registros suficientes dessa semana
para gerar um resumo completo. Continue registrando
o dia a dia do Bernardo!"

Não altere profile.py, whatsapp.py ou ingestion.
```

---

### PROMPT A2 — Registro de Conquistas como Marco

```
Analise o projeto Manolo (leia MANOLO.md para contexto).

Implemente registro de conquistas marcantes:

1. TABELA NO BANCO
Criar nova tabela em database.py:

CREATE TABLE IF NOT EXISTS marcos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    crianca_id UUID REFERENCES criancas(id),
    usuario_id UUID REFERENCES usuarios(id),
    descricao TEXT NOT NULL,
    data_marco DATE DEFAULT CURRENT_DATE,
    criado_em TIMESTAMPTZ DEFAULT NOW()
);

2. DETECÇÃO AUTOMÁTICA
Em agent/agent.py, após gerar a resposta do LLM,
verificar se a mensagem do usuário contém palavras-chave
de conquista: ["primeira vez", "conseguiu", "falou",
"andou", "fez sozinho", "pela primeira vez", "novo",
"conquistou", "surpreendeu"].

Se detectar, perguntar:
"🌟 Isso parece uma conquista especial do Bernardo!
Quer que eu registre como um marco importante?
Responda 'sim' para guardar para sempre."

3. COMANDO DIRETO
Usuário pode dizer "registrar marco" ou "guardar conquista"
seguido da descrição — salvar diretamente sem confirmação.

4. CONSULTA
Quando usuário perguntar "quais foram as conquistas"
ou "marcos do Bernardo", buscar na tabela marcos
e listar cronologicamente.

Não altere profile.py, whatsapp.py ou ingestion.
```

---

### PROMPT A3 — Modo Silencioso

```
Analise o projeto Manolo (leia MANOLO.md para contexto).

Implemente modo silencioso para pausar notificações proativas:

1. CONTROLE EM MEMÓRIA
Dicionário global em channels/main.py (ou telegram_bot.py):
silencio_ate = {}  # telefone -> datetime

2. ATIVAÇÃO
Detectar comandos: "/silencio", "modo silencioso",
"não perturbar", "pausar notificações".
Perguntar: "Por quantas horas? (ex: 4, 8, 24)"
Salvar: silencio_ate[telefone] = datetime.now() + timedelta(hours=X)
Confirmar: "Ok! Vou pausar as notificações por {X} horas.
Você pode me chamar quando quiser."

3. DESATIVAÇÃO
Detectar: "/ativar", "retomar notificações", "pode falar".
Remover do dicionário.
Confirmar: "Notificações reativadas!"

4. VERIFICAÇÃO
Antes de qualquer mensagem proativa (resumo semanal,
cobrança de checklist), verificar:
def esta_em_silencio(telefone: str) -> bool:
    if telefone in silencio_ate:
        if datetime.now() < silencio_ate[telefone]:
            return True
        else:
            del silencio_ate[telefone]
    return False

Não altere profile.py ou ingestion.
```

---

## 🟡 Média Prioridade

---

### PROMPT B1 — Comparação entre Períodos

```
Analise o projeto Manolo (leia MANOLO.md para contexto).

Implemente comparação temporal de evolução do Bernardo:

1. DETECÇÃO DE INTENÇÃO
Em agent/agent.py, detectar perguntas de comparação:
["compare", "diferença entre", "evoluiu", "melhorou",
"piorou", "antes e depois", "em relação a"].

2. EXTRAÇÃO DE PERÍODOS
Usar o LLM para extrair os dois períodos da pergunta:
"Compare a comunicação em abril com junho"
→ periodo_1 = abril/2026, periodo_2 = junho/2026

3. BUSCA NO BANCO
Criar função buscar_checklists_periodo(crianca_id, data_inicio, data_fim)
em core/memory.py que retorna agregados do período:
- Média de palavras ditas por dia
- Frequência de gestos
- Frequência de crises
- Padrão de sono (média de horas)
- Alimentos aceitos/recusados mais frequentes

4. PROMPT DE COMPARAÇÃO
Enviar os dois contextos para o LLM com instrução:
"Compare objetivamente esses dois períodos.
Destaque o que melhorou, o que piorou e o que
se manteve estável. Seja específico com dados.
Termine com uma avaliação geral do progresso."

Não altere profile.py, whatsapp.py ou ingestion.
```

---

### PROMPT B2 — Relatório para Sessão de Terapia

```
Analise o projeto Manolo (leia MANOLO.md para contexto).

Implemente geração de relatório pré-sessão:

1. DETECÇÃO DE INTENÇÃO
Detectar: "prepara resumo para", "relatório para",
"resumo antes da", "o que falar com a fono/TO/neuro".

2. IDENTIFICAÇÃO DO PROFISSIONAL
Extrair qual profissional da mensagem ou perguntar:
"Para qual profissional? (fono, TO, neuro, pediatra)"

3. BUSCA DE CONTEXTO
Buscar última sessão desse profissional nos documentos.
Buscar checklists desde a última sessão.
Buscar marcos registrados no período.

4. GERAÇÃO DO RELATÓRIO
Prompt para o LLM:
"Gere um relatório conciso para uma sessão de {especialidade}.
Inclua:
- Período coberto (desde última sessão)
- Principais observações do cotidiano relevantes para {especialidade}
- Conquistas do período
- Dificuldades observadas
- 3 perguntas sugeridas para fazer ao profissional
  baseadas no histórico

Use linguagem técnica apropriada para {especialidade}.
Seja objetivo e use dados concretos quando disponíveis."

5. FORMATO
Prefixo: "📋 Relatório para sessão de {especialidade} — {data}\n\n"
Ao final: "Quer que eu envie esse relatório para {nome_terapeuta}?"

Mensagens proativas nunca devem ser enviadas automaticamente
para terapeutas — apenas para perfis 'família' e 'admin'.
Para terapeutas, sempre aguardar confirmação do usuário
antes de enviar qualquer mensagem.

Não altere profile.py ou ingestion.
```

---

### PROMPT B3 — Alerta de Padrão Negativo

```
Analise o projeto Manolo (leia MANOLO.md para contexto).

Implemente detecção e alerta de padrões negativos:

1. VERIFICAÇÃO DIÁRIA
Criar função verificar_padroes(crianca_id) em agent/agent.py.
Disparar na primeira mensagem do dia (similar ao resumo semanal).

2. PADRÕES A DETECTAR
Buscar últimos 3 dias de checklists e verificar:
- Sono: acordou_noite = TRUE por 3 dias seguidos
- Humor: teve_crise = TRUE por 3 dias seguidos
- Alimentação: comeu_bem = FALSE por 3 dias seguidos
- Regressão: puxou_mao = 'sempre' por 3 dias
  (depois de período com 'às_vezes')

3. ALERTA
Se detectar padrão, avisar antes de responder
à mensagem do usuário:
"⚠️ Percebi que o Bernardo {descricao_padrao}
nos últimos 3 dias. Quer registrar alguma
observação sobre isso?"

4. CONTROLE DE FREQUÊNCIA
Não alertar o mesmo padrão mais de uma vez por semana.
Controle via dicionário em memória:
alertas_enviados[crianca_id] = {padrao: date}

Não altere profile.py, whatsapp.py ou ingestion.
```

---

### PROMPT B4 — Cobrança Conversacional do Checklist

```
Analise o projeto Manolo (leia MANOLO.md para contexto).

Implemente cobrança reativa do checklist com filosofia
conversacional — nunca formulário, sempre diálogo natural.

FILOSOFIA OBRIGATÓRIA:
O checklist não é preenchido pelo usuário — é extraído
de conversas naturais ao longo do dia. A cobrança ativa
existe só para o que não foi possível inferir.

1. EXTRAÇÃO SILENCIOSA
Em channels/main.py, para TODA mensagem recebida,
antes de responder, tentar extrair dados do checklist
do dia. Passar a mensagem para o LLM com prompt:
"Esta mensagem contém informações sobre a rotina
da criança? Se sim, extraia em JSON com os campos
disponíveis do checklist. Se não, retorne null."
Salvar silenciosamente sem avisar o usuário.

2. COBRANÇA REATIVA — UMA PERGUNTA POR VEZ
Na primeira mensagem do dia, verificar qual seção
prioritária está null em checklist de ontem.
Prioridade: sono > humor > comunicacao > alimentacao
> brincar > higiene > movimento > vestuario

Perguntar de forma natural sobre UMA seção apenas:
✅ "Bom dia, Ronaldo! Como foi o sono do Bernardo ontem?"
✅ "Boa noite! O Bernardo teve alguma crise hoje?"
❌ "Faltaram: sono, vestuário, higiene, movimento."

3. CONFIRMAÇÃO DE DATA
Ao extrair checklist de qualquer mensagem, sempre
confirmar a data de forma leve:
"Anotei isso para hoje, {data}. Correto?"
Se usuário corrigir, usar a data informada.

4. CHECKLIST PARCIAL
Usar INSERT ... ON CONFLICT (crianca_id, data)
DO UPDATE SET apenas os campos que vieram preenchidos.
Nunca sobrescrever campos já existentes com null.
Múltiplos registros do mesmo dia são mesclados.

Não altere profile.py, whatsapp.py ou agent.py diretamente.
```

---

### PROMPT B5 — Registro de Medicação

```
Analise o projeto Manolo (leia MANOLO.md para contexto).

Implemente registro e controle de medicação:

1. TABELAS NO BANCO
Adicionar em database.py:

CREATE TABLE IF NOT EXISTS medicacoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    crianca_id UUID REFERENCES criancas(id),
    nome TEXT NOT NULL,
    dose TEXT,
    horarios TEXT[],
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS medicacao_registros (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    crianca_id UUID REFERENCES criancas(id),
    medicacao_id UUID REFERENCES medicacoes(id),
    usuario_id UUID REFERENCES usuarios(id),
    data_hora TIMESTAMPTZ DEFAULT NOW(),
    administrado BOOLEAN DEFAULT TRUE,
    observacao TEXT
);

2. CADASTRO
Detectar: "cadastrar medicação", "novo remédio", "toma remédio".
Perguntar nome, dose e horários.
Confirmar antes de salvar.

3. REGISTRO DE DOSE
Detectar: "dei o remédio", "tomou [nome]", "administrei".
Registrar em medicacao_registros.
Confirmar: "Registrado! {nome} administrado às {hora}."

4. CONSULTA
"Deu o remédio hoje?" → listar o que foi e o que
não foi administrado nas últimas 24h.

Não altere profile.py, whatsapp.py ou ingestion.
```

---

## 🟢 Backlog

---

### PROMPT C1 — Preparação para Consulta Médica

```
Analise o projeto Manolo (leia MANOLO.md para contexto).

Implemente preparação para consultas e avaliações:

1. DETECÇÃO
Detectar: "consulta amanhã", "avaliação", "vai ao médico",
"prepara para consulta", "vai ao neuro/pediatra/psico".

2. COLETA DE CONTEXTO COMPLETO
Buscar:
- Perfil vivo atual do Bernardo
- Últimas avaliações (Bayley e similares)
- Checklists dos últimos 30 dias
- Documentos dos últimos 90 dias
- Marcos registrados
- Medicações ativas

3. GERAÇÃO DO DOCUMENTO
Prompt para o LLM com temperature=0.2:
"Gere um documento completo de preparação para consulta médica.
Inclua:
1. Resumo do desenvolvimento atual (baseado no perfil vivo)
2. Histórico relevante desde a última consulta
3. Conquistas do período
4. Preocupações e dificuldades observadas
5. Padrões relevantes identificados nos registros diários
6. Perguntas sugeridas para o médico baseadas no histórico
7. Medicações em uso

Use linguagem acessível para o médico mas precisa.
Cite datas e dados concretos."

4. ENTREGA
Responder com o documento completo.
Oferecer: "Quer que eu envie isso para algum terapeuta?"

Mensagens nunca devem ser enviadas automaticamente
para terapeutas — sempre aguardar confirmação explícita.

Não altere profile.py, whatsapp.py ou ingestion.
```

---

### PROMPT C2 — Diário Livre da Família

```
Analise o projeto Manolo (leia MANOLO.md para contexto).

Implemente diário livre — registro informal sem estrutura:

1. TABELA NO BANCO
Adicionar em database.py:

CREATE TABLE IF NOT EXISTS diario (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    crianca_id UUID REFERENCES criancas(id),
    usuario_id UUID REFERENCES usuarios(id),
    conteudo TEXT NOT NULL,
    data DATE DEFAULT CURRENT_DATE,
    embedding VECTOR(1536),
    criado_em TIMESTAMPTZ DEFAULT NOW()
);

2. DETECÇÃO
Detectar: "quero registrar", "anota aí", "guarda isso",
"no diário", ou qualquer texto longo que não seja
checklist nem pergunta.

3. INDEXAÇÃO
Gerar embedding do conteúdo e salvar na tabela diario.
Confirmar: "Anotado no diário de {data}! 📝"

4. BUSCA
Incluir diário na busca semântica de core/memory.py
junto com documento_chunks.
Quando relevante, o agente cita entradas do diário
nas respostas.

Não altere profile.py ou ingestion existente.
```

---

### PROMPT C3 — Transcrição de Sessão de Terapia

```
Analise o projeto Manolo (leia MANOLO.md para contexto).

Implemente transcrição e indexação de sessões gravadas:

1. DETECÇÃO
Quando receber áudio longo (> 3 minutos) ou quando
usuário disser "gravar sessão", "áudio da sessão",
"gravação da fono/TO".

2. FLUXO
a) Confirmar: "Este áudio é de uma sessão de terapia?
   Se sim, de qual especialidade e qual a data?"
b) Aguardar confirmação
c) Transcrever com Groq Whisper large-v3
d) Enviar transcrição para LLM com prompt:
   "Analise essa transcrição de sessão de {especialidade}.
   Extraia:
   - Principais observações do terapeuta
   - Atividades realizadas e reação da criança
   - Orientações para a família
   - Próximos objetivos
   Organize em tópicos claros."
e) Salvar transcrição completa + análise como documento
   na tabela documentos com tipo='relatorio_sessao'
f) Indexar chunks no pgvector

3. CONFIRMAÇÃO
"Sessão de {especialidade} de {data} indexada!
Principais pontos: {resumo em 3 linhas}"

Não altere profile.py ou lógica existente de ingestão
— apenas adicione o novo fluxo de detecção em main.py.
```

---

### PROMPT C4 — Relatório de Evolução Detalhado

```
Analise o projeto Manolo (leia MANOLO.md para contexto).

Implemente relatório detalhado de evolução para terapeutas:

1. GATILHO
Comando: "relatório de evolução", "como evoluiu",
"progresso do Bernardo".
Perguntar período: "De quando até quando?"
Ou aceitar: "último mês", "últimas 4 semanas", "desde janeiro".

2. DADOS
Buscar para o período:
- Checklists agregados por semana
- Documentos e laudos do período
- Marcos registrados
- Avaliações formais se houver

3. ANÁLISE POR DOMÍNIO
Prompt para o LLM com os dados:
"Gere um relatório de evolução detalhado por domínio:
- Comunicação e linguagem
- Motor grosso e fino
- Alimentação e seletividade
- Sono e regulação
- Interação social e brincar

Para cada domínio: estado no início do período,
estado atual, tendência, dados que suportam.
Use linguagem técnica. Cite datas e dados concretos.
Conclua com avaliação geral do período."

4. FORMATO
Documento estruturado com seções por domínio.
Oferecer ao final: "Quer que eu envie para algum terapeuta?"

Não altere profile.py, whatsapp.py ou ingestion.
```

---

## Como usar este arquivo

```
1. Escolha um prompt
2. Cole no chat do Gemini com o projeto aberto
3. Revise o código gerado antes de commitar
4. Teste localmente
5. Marque como concluído aqui
6. Commit e deploy no Render
```

---

## Status

| Prompt | Feature | Status |
|---|---|---|
| A1 | Resumo semanal automático | ☐ |
| A2 | Registro de conquistas | ☐ |
| A3 | Modo silencioso | ☐ |
| B1 | Comparação entre períodos | ☐ |
| B2 | Relatório para sessão | ☐ |
| B3 | Alerta de padrão negativo | ☐ |
| B4 | Cobrança conversacional do checklist | ☐ |
| B5 | Registro de medicação | ☐ |
| C1 | Preparação para consulta | ☐ |
| C2 | Diário livre da família | ☐ |
| C3 | Transcrição de sessão | ☐ |
| C4 | Relatório de evolução | ☐ |
