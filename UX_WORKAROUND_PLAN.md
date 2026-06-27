# Plano de Implementação: Contorno de UX para Ausência de "Digitando..."

## 1. Objetivo

Implementar uma solução de contorno para a falta do indicador "digitando..." na API Oficial do WhatsApp Business. A solução consiste em enviar uma mensagem estática e imediata para o usuário assim que uma mensagem é recebida, informando que a solicitação está sendo processada. Isso melhora a experiência do usuário (UX), dando um feedback instantâneo e gerenciando a expectativa durante o tempo de processamento do LLM.

## 2. Arquivo a ser modificado

- `channels/main.py`

## 3. Lógica de Implementação

A alteração será feita na função `receive_message`, que gerencia o webhook de recebimento de mensagens.

1.  **Localizar o ponto de inserção:** A nova lógica será adicionada dentro do bloco que processa mensagens de texto (`if tipo == "text":`).

2.  **Análise do fluxo de áudio:** O fluxo de recebimento de áudio (`elif tipo == "audio":`) já implementa um comportamento semelhante, enviando a mensagem "Recebi seu áudio! Vou processá-lo e te aviso em instantes." antes do processamento pesado. Replicaremos essa mesma abordagem para as mensagens de texto.

3.  **Adicionar tarefa de feedback:** Antes da linha `background_tasks.add_task(processar_e_enviar_resposta, ...)` no bloco de texto, adicionaremos uma nova tarefa para enviar a mensagem de confirmação.

    - **Mensagem Proposta:** "Consultando..."
    - **Função a ser utilizada:** `enviar_mensagem_async`

4.  **Ordem das Tarefas:** A tarefa de envio da mensagem de confirmação será adicionada às `background_tasks` *antes* da tarefa de processamento da resposta do agente. Isso garante que o feedback de UX seja enviado primeiro, conforme o objetivo.

## 4. Pseudocódigo da Alteração

```python
# Em channels/main.py, dentro de @app.post("/webhook")

# ... (código de verificação de usuário)

if tipo == "text":
    texto = mensagem.get("text", {}).get("body", "")
    if not texto: return Response(status_code=200)
    
    logger.info(f"Mensagem de texto recebida de {nome_usuario}: {texto}")

    # <<< NOVA LINHA ADICIONADA AQUI >>>
    background_tasks.add_task(enviar_mensagem_async, "Consultando...", telefone_remetente)
    
    # Linha existente (continua igual)
    background_tasks.add_task(processar_e_enviar_resposta, texto, telefone_remetente, nome_usuario, perfil_usuario)

# ... (restante do código)
```

## 5. Validação

Após a implementação, o fluxo esperado ao enviar uma mensagem de texto para o Manolo será:

1.  Receber imediatamente a resposta "Consultando...".
2.  Alguns segundos depois, receber a resposta completa e processada pelo agente.

Este plano alinha-se com a **Solução 1** proposta e é a forma mais rápida e segura de atingir o objetivo de UX desejado.
