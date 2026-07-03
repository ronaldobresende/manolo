import os
import json
from dotenv import load_dotenv
from openai import OpenAI
import sys

# Ajustar o path para conseguir importar do diretorio 'core'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.schemas import LLMChecklistResponse

# Carrega variáveis de ambiente (como OPENAI_API_KEY)
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

prompt_checklist = """Você é um extrator de dados de rotina infantil.
Analise a mensagem do usuário.
A data de hoje em São Paulo é 2026-07-01 (Quarta-feira). O horário atual é 15:00.

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
- O terapeuta NÃO precisa relatar comportamentos domésticos. Deixe como null apenas o que não for dito, mas extraia rigorosamente tudo o que for relatado!"""

# Aqui você pode colar qualquer mensagem ou lista de mensagens que quiser testar
mensagens_teste = [
    "Na terapia ele colaborou com a troca da fralda dentro do que é possível para ele. E as transições de sala e espera foi tranquilo também",
    "Trabalhamos coordenação motora grossa com bom engajamento e equilíbrio, estimulacao sensorial em bolinha de gel, com uso bimanual fazendo transferência de um pote para outro. Brincou de esconde esconde. Escalou com fortalecimento de MMSS",
    "Explorou equipamentos suspensos. E já entende a hora do tchau, saiu do colo da Denise sem grudar no pescoço assim que ouviu início da música, ficando sentado na minha perna, esperando a finalização solicitando voltar com a mãe. Hoje já associa a música com a hora de finalização da terapia e transição de sala."
]

# Simulação do banco de dados (o que já temos acumulado no dia)
db_acumulado = {
    "rotina": {"aceitou_transicao": None, "teve_escola": None},
    "vestuario": {"colaborou_roupa": None, "incomodo_sensorial": None},
    "comunicacao": {"usou_gestos": None, "palavras_ditas": [], "apontou": None},
    "brincar": {"com_que_brincou": [], "fez_faz_de_conta": None},
    "movimento": {"atividades": [], "caiu_muito": None},
    "sessoes_terapia": []
}

def simular_upsert_banco(campos_novos):
    """Simula as regras de COALESCE, array_cat e CONCAT_WS do PostgreSQL."""
    for categoria, campos in campos_novos.items():
        if not campos or categoria not in db_acumulado:
            continue
            
        # Regra para ARRAYS de Sessões de Terapia
        if categoria == "sessoes_terapia":
            if not isinstance(db_acumulado.get(categoria), list):
                db_acumulado[categoria] = []
            for sessao in campos: # campos aqui é uma lista de dicts
                # Se tiver a mesma especialidade, concatena notas
                existente = next((s for s in db_acumulado[categoria] if s.get("especialidade") == sessao.get("especialidade")), None)
                if existente:
                    existente["notas_sessao"] = f"{existente.get('notas_sessao', '')}\n{sessao.get('notas_sessao', '')}"
                else:
                    db_acumulado[categoria].append(sessao)
            continue
            
        for chave, valor_novo in campos.items():
            valor_atual = db_acumulado[categoria].get(chave)
            
            if valor_novo is None:
                continue
                
            # Regra para ARRAYS (array_cat no SQL)
            if isinstance(valor_novo, list):
                if valor_atual is None:
                    db_acumulado[categoria][chave] = []
                db_acumulado[categoria][chave].extend(valor_novo)
                
            # Regra para OBSERVACOES (CONCAT_WS no SQL)
            elif categoria == "observacoes":
                if valor_atual is None:
                    db_acumulado[categoria][chave] = valor_novo
                else:
                    db_acumulado[categoria][chave] = f"{valor_atual}\n{valor_novo}"
                        
            # Regra para ESCALARES boolean/str (COALESCE no SQL)
            else:
                db_acumulado[categoria][chave] = valor_novo


def rodar_teste_extracao():
    print("=== TESTE DE EXTRAÇÃO SEQUENCIAL (SIMULAÇÃO DE UPSERT) ===\n")
    
    for i, mensagem in enumerate(mensagens_teste, 1):
        print(f"[{i}/{len(mensagens_teste)}] Processando mensagem: '{mensagem}' ...")

        try:
            response = client.beta.chat.completions.parse(
                model="gpt-4o-2024-08-06",
                messages=[
                    {"role": "system", "content": prompt_checklist},
                    {"role": "user", "content": mensagem}
                ],
                response_format=LLMChecklistResponse,
                temperature=0.0
            )
            
            resultado = response.choices[0].message.parsed
            
            if resultado.contem_dados and resultado.relatos:
                campos = resultado.relatos[0].campos_preenchidos.model_dump(exclude_none=True)
                simular_upsert_banco(campos)
                
        except Exception as e:
            print(f"Erro ao processar: {e}")

    print("\n" + "="*60)
    print("ESTADO FINAL ACUMULADO NO BANCO (FIM DO DIA):")
    print("="*60)
    
    # Limpa valores nulos e listas vazias apenas para exibir mais bonito
    db_final = {}
    for cat, campos in db_acumulado.items():
        if isinstance(campos, list):
            if campos:
                db_final[cat] = campos
        else:
            campos_preenchidos = {k: v for k, v in campos.items() if v is not None and v != []}
            if campos_preenchidos:
                db_final[cat] = campos_preenchidos
            
    print(json.dumps(db_final, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    rodar_teste_extracao()
