# Plano de Correção: Indicador "Digitando" no WhatsApp

**Problema:** O indicador "digitando" (`typing indicator`) no WhatsApp não funciona como esperado. Ele é ativado, mas desaparece antes que a resposta do agente seja enviada, pois o processamento da mensagem (chamada ao LLM) é demorado e o status de "digitando" expira no aplicativo do usuário.

**Causa Raiz:** O código atual ativa o indicador de "digitando" uma única vez no início do processamento e o desativa no final. A API do WhatsApp requer que o status de "digitando" seja enviado periodicamente para mantê-lo ativo na tela do usuário.

**Plano de Implementação:**

1.  **Refatorar o `main.py`**: A lógica de processamento de mensagens de texto no webhook `/webhook` será reestruturada.

2.  **Criar uma Função Gerenciadora (`process_with_typing`)**: Será criada uma nova função assíncrona, `process_with_typing`, que orquestrará o processo. Esta função receberá a pergunta e as informações do remetente.

3.  **Execução em Paralelo com `asyncio`**: Dentro de `process_with_typing`, duas tarefas serão executadas em paralelo usando `asyncio.gather` ou um mecanismo similar:
    *   **Tarefa 1: Processamento da Mensagem**: A função síncrona `perguntar_ao_manolo` será executada em uma thread separada usando `asyncio.to_thread`, como já está sendo feito.
    *   **Tarefa 2: Manutenção do Indicador**: Uma nova corrotina será criada. Ela entrará em um loop que:
        *   Envia `await enviar_typing(telefone, typing_on=True)`.
        *   Espera por um período seguro antes que o indicador expire (ex: `await asyncio.sleep(4)`).
        *   Continuará em loop até que a Tarefa 1 seja concluída.

4.  **Cancelamento e Finalização**:
    *   Quando a Tarefa 1 (processamento) for concluída, a Tarefa 2 (manutenção do indicador) será cancelada.
    *   O indicador de "digitando" será explicitamente desativado enviando `await enviar_typing(telefone, typing_on=False)`.
    *   A resposta obtida da Tarefa 1 será finalmente enviada ao usuário.

5.  **Tratamento de Erros**: A nova função incluirá tratamento de exceções para garantir que, mesmo se o processamento da mensagem falhar, o indicador de "digitando" seja desativado e uma mensagem de erro apropriada seja enviada.

Essa abordagem garante que o usuário veja o indicador de "digitando" durante todo o tempo de processamento, melhorando significativamente a experiência do usuário.
