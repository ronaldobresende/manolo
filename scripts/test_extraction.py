import os
import sys

# Adiciona o diretório raiz do projeto ao path para importar os módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.clients import get_openai_client
from core.schemas import LLMChecklistResponse
from core.config import settings

def test_silent_extraction():
    # Mensagem de teste da Gilsele
    mensagem_teste = """[22:57, 07/07/2026] Gilsele: Comeu bolacha , maça, pipoquinha 
Almoçou arroz e carne 
Brincou de bolinha pula pula, jogava e buscava 
Pegou as frutas p mim falar os nomes
Esta conseguindo dar uns pulinhos, fez bichinho de massinha, 
Colocou a capivara e o peixe encima do gangorra de brinquedo e balançou
Falou: dada,dada,dada 
Ia , ia lala, kade kade, esta falando bastante eu nao entendi
Esta abrindo a mãozinha p mim colocar sabone, ele passa na barriga, nas pernas 
Dormiu 12:20 
Acordou 13:35
[22:59, 07/07/2026] Gilsele: Nao chorou p querer a mae dele, ficou feliz o dia inteiro, sem birra estava muito fofo hoje"""

    prompt_extracao = f"""Você é um extrator de dados de rotina infantil.
Analise a mensagem do usuário.
A data de hoje em São Paulo é 2026-07-09 (Quinta-feira). O horário atual é 22:30.

REGRAS DE DATA E CONTEXTO:
- NUNCA infira que um evento foi "ontem" ou outra data apenas porque o usuário usou o passado ("ele dormiu mal").
- Sempre que a data não for EXPLÍCITA, retorne data_referencia_iso = null (assumiremos hoje).
- Se a mensagem descrever eventos de múltiplos dias explicitamente, crie múltiplos itens na lista 'relatos'.
- AMBIGUIDADE (CONFIRMAÇÃO): Marque 'data_ambigua = True' APENAS se o usuário mencionar um dia vago E O CONTEXTO FOR IMPOSSÍVEL DE DEDUZIR.
- Se o usuário disser "comeu maçã", e você não souber se foi café ou almoço, anote no campo 'notas' da alimentação.

REGRAS DE DUPLA EXTRAÇÃO (TERAPEUTAS):
- Se o usuário atual for um terapeuta, foque em preencher a lista 'sessoes_terapia' com os detalhes da sessão (horários, notas clínicas, especialidade).
- SIMULTANEAMENTE, extraia TODOS os comportamentos descritos (mesmo os que pareçam rotineiros) e distribua-os nas categorias apropriadas. Exemplos:
  - "Colaborou com a troca da fralda" -> vestuario.colaborou_roupa = True
  - Engajamento motor -> movimento.atividades
  - Brinquedos usados -> brincar.com_que_brincou
- O terapeuta NÃO precisa relatar comportamentos domésticos. Deixe como null apenas o que não for dito, mas extraia rigorosamente tudo o que for relatado!

"""


    client = get_openai_client()
    
    # Você pode forçar um modelo aqui se quiser (ex: "gpt-4o" ou "gpt-5")
    # Forçando GPT-5 para ver o poder de reasoning
    modelo = "gpt-5" 
    print(f"Executando simulação de extração com o modelo: {modelo}")
    print("-" * 50)
    
    try:
        kwargs = {"temperature": 0} if "gpt-4" in modelo else {}
        response = client.beta.chat.completions.parse(
            model=modelo,
            response_format=LLMChecklistResponse,
            messages=[
                {"role": "system", "content": prompt_extracao},
                {"role": "user", "content": mensagem_teste},
            ],
            **kwargs
        )
        resultado = response.choices[0].message.parsed
        # Exibe em formato JSON bonitinho, sem imprimir chaves nulas
        print(resultado.model_dump_json(indent=2, exclude_none=True))
        
    except Exception as e:
        print(f"Erro durante a extração: {e}")

if __name__ == "__main__":
    test_silent_extraction()
