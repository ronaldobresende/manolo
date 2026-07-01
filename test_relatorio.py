import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# O JSON gerado pelo modelo 100% Acumulativo
contexto_acumulativo = {
  "alimentacao": {
    "aceitou": [
      "mamou com a Vivi de manhã",
      "pipoquinha",
      "maçã",
      "bolacha",
      "chocolate",
      "maçã da mesa",
      "mais bolacha",
      "mamadeira às 15:00",
      "bolacha às 16:30",
      "bastante água"
    ],
    "recusou": [
      "pão",
      "almoço"
    ]
  },
  "comunicacao": {
    "palavras_ditas": [
      "Doog",
      "azul",
      "dadada",
      "keka"
    ]
  },
  "brincar": {
    "com_que_brincou": [
      "brincou na areia",
      "fazer casquinha",
      "massinha"
    ],
    "modo": "com_adulto",
    "fez_faz_de_conta": True
  },
  "movimento": {
    "atividades": [
      "subindo e descendo do sofá",
      "correndo pelo quintal"
    ]
  },
  "tela": {
    "usou_tela": True
  },
  "observacoes": {
    "conquistas": "foi na bolsa e pegou chocolate sozinho\nEle mesmo está indo pegar as coisas para comer."
  }
}

# O JSON gerado pelo modelo Híbrido (Eventos + Acumulativo)
contexto_hibrido = {
  "eventos_alimentacao": [
    {"tipo_refeicao": "livre", "aceitou": ["mamadeira"], "notas": "Mamou com a Vivi."},
    {"tipo_refeicao": "livre", "aceitou": ["pipoquinha", "maçã", "bolacha"], "recusou": ["pão"]},
    {"tipo_refeicao": "almoco", "recusou": ["almoço"], "comeu_bem": False},
    {"tipo_refeicao": "livre", "aceitou": ["chocolate"], "notas": "Foi na bolsa dele e achou chocolate."},
    {"tipo_refeicao": "livre", "aceitou": ["maçã"], "notas": "Pegou na mesa."},
    {"tipo_refeicao": "livre", "aceitou": ["bolacha"], "notas": "Pegou mais bolacha."},
    {"tipo_refeicao": "livre", "aceitou": ["comida"], "notas": "Foi na bolsa pegar sozinho."},
    {"horario": "15:00", "tipo_refeicao": "livre", "aceitou": ["mamadeira"]},
    {"horario": "11:30", "notas": "Ofereceu comida"},
    {"horario": "16:30", "tipo_refeicao": "livre", "aceitou": ["bolacha"], "notas": "Comeu mais bolacha 2."},
    {"tipo_refeicao": "livre", "aceitou": ["água"], "notas": "Bebeu bastante água"}
  ],
  "eventos_comunicacao": [
    {"horario": "16:30", "contexto": "em casa vendo TV", "palavras_ditas": ["Doog"], "tipo_emissao": "espontanea"},
    {"contexto": "na fono", "palavras_ditas": ["azul", "dadada"]},
    {"notas": "falou mais coisas mas não deu pra entender"},
    {"palavras_ditas": ["keka"], "tipo_emissao": "espontanea"}
  ],
  "acumulativos": {
    "tela": {"usou_tela": True},
    "brincar": {
      "com_que_brincou": ["brincou na areia", "subiu e desceu do sofá", "correu pelo quintal", "fazer casquinha", "massinha"],
      "modo": "misto",
      "fez_faz_de_conta": True
    },
    "movimento": {
      "atividades": ["subiu e desceu do sofá", "correu pelo quintal"]
    }
  }
}

prompt_sistema = """Você é o Manolo, um assistente empático para desenvolvimento infantil.
Responda à pergunta da família baseando-se EXCLUSIVAMENTE nos dados JSON de rotina fornecidos.
Fale em um tom caloroso, amigável e direto com a família."""

pergunta_usuario = "Manolo, me conte como foi o dia do Bernardo?"

def gerar_relatorio(nome_modelo, contexto_json):
    print(f"\n=======================================================")
    print(f"GERANDO RESUMO COM BASE NO MODELO: {nome_modelo}")
    print(f"=======================================================")
    
    prompt_usuario = f"DADOS DO DIA:\n{json.dumps(contexto_json, ensure_ascii=False, indent=2)}\n\nPERGUNTA DA FAMÍLIA:\n{pergunta_usuario}"
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario}
        ],
        temperature=0.7
    )
    
    print(response.choices[0].message.content)

if __name__ == "__main__":
    gerar_relatorio("100% ACUMULATIVO (Atual)", contexto_acumulativo)
    gerar_relatorio("HÍBRIDO COM EVENTOS", contexto_hibrido)
    print("\n")
