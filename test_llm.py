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
- AMBIGUIDADE (CONFIRMAÇÃO): Marque 'data_ambigua = True' APENAS se o usuário mencionar um dia vago E O CONTEXTO FOR IMPOSSÍVEL DE DEDUZIR (ex: "semana passada", "aquele dia").
- Se o usuário disser "comeu maçã", e você não souber se foi café ou almoço, anote no campo 'notas' da alimentação, NÃO marque como ambíguo. Evite ao máximo interromper a família."""

# Aqui você pode colar qualquer mensagem ou lista de mensagens que quiser testar
mensagens_teste = [
    "Na parte da manhã ,mamou com a Vivi,  comeu pipoquinha,maça, bolacha, nao quis pão\nNão quis almoçar\nFoi la na bolsa dele achou chocolate comeu,foi lá na  mesa e pegou maça, pegou mais bolacha",
    "Ele mesmo esta indo pegar as coisas p comer",
    "15:00 de mamadeira",
    "11:30 ja fui oferendo a comida",
    "16:30 comeu mais bolacha 2",
    "Brincou na areia, ficou subindo de descendo do sofá, fique correndo pelo quintal eu atrás brincando, brincamos de fazer casquinha 😂😂",
    "Brincamos de massinha",
    "16:30 vo ligou a TV, Bernardo começou a falar Doog",
    "Bebeu bastante água",
    "Lá na fono ele falou azul, dadada",
    "Falou mais coisa nao deu p entender",
    "Ficou falando keka, keka..."
]

# Simulação do banco de dados (o que já temos acumulado no dia)
db_acumulado = {
    "alimentacao": {"aceitou": [], "recusou": [], "comeu_bem": None, "comeu_sentado": None, "utensilio": None},
    "comunicacao": {"usou_gestos": None, "palavras_ditas": [], "apontou": None, "puxou_mao": None, "respondeu_nome": None, "imitou": None},
    "brincar": {"com_que_brincou": [], "modo": None, "fez_faz_de_conta": None, "tempo_sem_tela_minutos": None},
    "movimento": {"atividades": [], "caiu_muito": None, "buscou_colo": None},
    "tela": {"usou_tela": None, "tempo_minutos": None, "conteudo": None, "reacao_retirada": None},
    "observacoes": {"conquistas": None, "dificuldades": None, "diferente_hoje": None}
}

def simular_upsert_banco(campos_novos):
    """Simula as regras de COALESCE, array_cat e CONCAT_WS do PostgreSQL."""
    for categoria, campos in campos_novos.items():
        if not campos or categoria not in db_acumulado:
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
        campos_preenchidos = {k: v for k, v in campos.items() if v is not None and v != []}
        if campos_preenchidos:
            db_final[cat] = campos_preenchidos
            
    print(json.dumps(db_final, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    rodar_teste_extracao()
