"""
test_llm_eventos.py — Teste de extração com modelo HÍBRIDO (Eventos + Acumulativos).

Alimentação, Comunicação e Sono viram LISTAS DE EVENTOS (1-para-N).
As demais tabelas continuam acumulativas (UPSERT).
"""
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ============================================================
# MODELOS DE EVENTOS (1-para-N) — substituem os modelos antigos
# ============================================================

class AlimentacaoEventoModel(BaseModel):
    horario: Optional[str] = Field(None, description="Horário aproximado do evento (formato HH:MM). Se não mencionado, retorne null.")
    tipo_refeicao: Optional[Literal['cafe_manha', 'lanche', 'almoco', 'jantar', 'livre']] = Field(None, description="Tipo da refeição. Use 'livre' se for um lanche fora de hora, mamadeira avulsa ou água.")
    aceitou: Optional[List[str]] = Field(None, description="Alimentos aceitos neste evento específico. Inclua mamadeiras, líquidos, água, lanches.")
    recusou: Optional[List[str]] = Field(None, description="Alimentos recusados neste evento específico.")
    comeu_bem: Optional[bool] = Field(None, description="Se comeu bem neste evento.")
    comeu_sentado: Optional[bool] = Field(None, description="Se comeu sentado à mesa ou cadeirão.")
    utensilio: Optional[Literal['colher', 'garfo', 'mao', 'misto']] = Field(None, description="Utensílio usado.")
    notas: Optional[str] = Field(None, description="Contexto extra deste evento (ex: 'foi na bolsa pegar sozinho').")

class ComunicacaoEventoModel(BaseModel):
    horario: Optional[str] = Field(None, description="Horário aproximado (formato HH:MM).")
    contexto: Optional[str] = Field(None, description="Onde/quando aconteceu (ex: 'na fono', 'em casa vendo TV', 'no quintal').")
    palavras_ditas: Optional[List[str]] = Field(None, description="Palavras ou sons com intenção de fala emitidos neste momento. Sons aproximados (ex: 'dadada', 'keka', 'doog') TAMBÉM contam.")
    tipo_emissao: Optional[Literal['espontanea', 'imitacao', 'tentativa', 'gesto_isolado']] = Field(None, description="Tipo de emissão comunicativa.")
    notas: Optional[str] = Field(None, description="Detalhes extras (ex: 'falou mais coisas mas não deu pra entender').")

class SonoEventoModel(BaseModel):
    horario_inicio: Optional[str] = Field(None, description="Hora em que dormiu (formato HH:MM).")
    horario_fim: Optional[str] = Field(None, description="Hora em que acordou (formato HH:MM).")
    tipo: Optional[Literal['noturno', 'cochilo', 'despertar_noturno']] = Field(None, description="Tipo do evento de sono.")
    notas: Optional[str] = Field(None, description="Observações sobre o sono.")

# ============================================================
# MODELOS ACUMULATIVOS (mantidos iguais — 1-para-1 com UPSERT)
# ============================================================

class TelaModel(BaseModel):
    usou_tela: Optional[bool] = Field(None, description="Se usou telas (celular, TV, tablet).")
    tempo_minutos: Optional[int] = Field(None, description="Tempo total de tela em minutos.")
    conteudo: Optional[str] = Field(None, description="O que assistiu ou jogou.")
    reacao_retirada: Optional[Literal['tranquilo', 'resistencia', 'crise']] = Field(None, description="Reação ao retirar a tela.")

class BrincarModel(BaseModel):
    com_que_brincou: Optional[List[str]] = Field(None, description="Quais brinquedos ou atividades. Inclua contexto (ex: 'brincou na areia', 'massinha').")
    modo: Optional[Literal['sozinho', 'com_adulto', 'misto']] = Field(None, description="Como brincou.")
    fez_faz_de_conta: Optional[bool] = Field(None, description="Se fez brincadeira simbólica (ex: fazer casquinha, comidinha, imitar adultos).")
    tempo_sem_tela_minutos: Optional[int] = Field(None, description="Tempo estimado de brincadeira sem telas.")

class HumorModel(BaseModel):
    humor_geral: Optional[Literal['muito_bom', 'bom', 'regular', 'agitado', 'difícil']] = Field(None, description="Humor predominante.")
    teve_crise: Optional[bool] = Field(None, description="Se teve crise de choro ou birra.")
    o_que_acalmou: Optional[str] = Field(None, description="O que ajudou a acalmar.")
    notas: Optional[str] = Field(None, description="Notas sobre humor.")

class HigieneModel(BaseModel):
    banho: Optional[Literal['tranquilo', 'resistencia', 'crise']] = Field(None, description="Como foi o banho.")
    escovou_dentes: Optional[bool] = None
    sinalizou_banheiro: Optional[bool] = None

class VestuarioModel(BaseModel):
    colaborou_roupa: Optional[bool] = None
    incomodo_sensorial: Optional[bool] = None

class MovimentoModel(BaseModel):
    atividades: Optional[List[str]] = Field(None, description="Atividades físicas ou motoras (ex: 'subiu e desceu do sofá', 'correu pelo quintal').")
    caiu_muito: Optional[bool] = None
    buscou_colo: Optional[bool] = None

class RotinaModel(BaseModel):
    guardou_brinquedos: Optional[bool] = None
    ajudou_tarefa: Optional[bool] = None
    aceitou_transicao: Optional[bool] = None

class ObservacoesModel(BaseModel):
    conquistas: Optional[str] = Field(None, description="Avanços de autonomia, marcos positivos. NÃO coloque aqui o que couber nos campos específicos.")
    dificuldades: Optional[str] = Field(None, description="Desafios que não couberam nos campos específicos.")
    diferente_hoje: Optional[str] = Field(None, description="Qualquer observação qualitativa solta.")

# ============================================================
# SCHEMA PRINCIPAL (HÍBRIDO)
# ============================================================

class CamposPreenchidosHibrido(BaseModel):
    # EVENTOS (listas — cada item é um evento separado)
    alimentacao: Optional[List[AlimentacaoEventoModel]] = Field(None, description="Lista de eventos de alimentação detectados na mensagem. Cada refeição, lanche ou mamadeira é um evento separado.")
    comunicacao: Optional[List[ComunicacaoEventoModel]] = Field(None, description="Lista de eventos de comunicação. Cada contexto distinto (fono, casa, TV) é um evento separado.")
    sono: Optional[List[SonoEventoModel]] = Field(None, description="Lista de eventos de sono. Noturno, cochilo e despertares são eventos separados.")
    
    # ACUMULATIVOS (objetos únicos — UPSERT no dia)
    tela: Optional[TelaModel] = None
    brincar: Optional[BrincarModel] = None
    humor: Optional[HumorModel] = None
    higiene: Optional[HigieneModel] = None
    vestuario: Optional[VestuarioModel] = None
    movimento: Optional[MovimentoModel] = None
    rotina: Optional[RotinaModel] = None
    observacoes: Optional[ObservacoesModel] = None

class RelatoDiarioHibrido(BaseModel):
    data_referencia_iso: Optional[str] = Field(None, description="Data no formato YYYY-MM-DD. Se não explícita, retorne null.")
    campos_preenchidos: CamposPreenchidosHibrido = Field(default_factory=CamposPreenchidosHibrido)

class LLMChecklistResponseHibrido(BaseModel):
    contem_dados: bool = Field(description="Se a mensagem contém dados de rotina.")
    data_ambigua: bool = Field(False)
    correcao_retroativa: bool = Field(False)
    data_destino_correcao: Optional[str] = None
    relatos: List[RelatoDiarioHibrido] = Field(default_factory=list)
    campos_ausentes: List[str] = Field(default_factory=list)

# ============================================================
# PROMPT
# ============================================================

prompt_checklist = """Você é um extrator de dados de rotina infantil.
Analise a mensagem do usuário.
A data de hoje em São Paulo é 2026-07-01 (Quarta-feira). O horário atual é 15:00.

REGRAS DE EXTRAÇÃO:
- Para ALIMENTAÇÃO, COMUNICAÇÃO e SONO: extraia como LISTA DE EVENTOS separados.
  Cada refeição/lanche/mamadeira é um evento distinto de alimentação.
  Cada contexto diferente de fala (fono, casa, TV) é um evento distinto de comunicação.
  Cada período de sono (noturno, cochilo) é um evento distinto.
- Para as demais categorias (tela, brincar, humor, etc.): extraia como objeto único (resumo do dia).
- NUNCA infira datas. Se não for explícita, retorne data_referencia_iso = null.
- Se o usuário disser "comeu maçã" sem contexto de refeição, use tipo_refeicao = "livre".

REGRAS DE AGRUPAMENTO E CONTEXTO:
- AGRUPAMENTO DE ALIMENTAÇÃO: Agrupe todos os alimentos consumidos no mesmo momento ou contexto em um ÚNICO evento. NÃO crie um evento separado para cada alimento se eles aconteceram na mesma refeição.
- ROTEAMENTO DE CONQUISTAS: Se a nota de QUALQUER evento contiver marcos de desenvolvimento, demonstrações de autonomia (ex: "foi na bolsa pegar sozinho", "comeu sozinho") ou comportamentos muito atípicos, NÃO deixe essa informação presa nas 'notas' do evento. COPIE OBRIGATORIAMENTE para o campo global `observacoes.conquistas` ou `observacoes.dificuldades`."""

# ============================================================
# MENSAGENS DE TESTE
# ============================================================

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

# ============================================================
# SIMULAÇÃO DO BANCO DE DADOS
# ============================================================

# EVENTOS: listas que só crescem (INSERT simples)
db_eventos = {
    "alimentacao": [],
    "comunicacao": [],
    "sono": []
}

# ACUMULATIVOS: UPSERT como antes
db_acumulado = {
    "tela": {"usou_tela": None, "tempo_minutos": None, "conteudo": None, "reacao_retirada": None},
    "brincar": {"com_que_brincou": [], "modo": None, "fez_faz_de_conta": None, "tempo_sem_tela_minutos": None},
    "movimento": {"atividades": [], "caiu_muito": None, "buscou_colo": None},
    "humor": {"humor_geral": None, "teve_crise": None, "o_que_acalmou": None, "notas": None},
    "higiene": {"banho": None, "escovou_dentes": None, "sinalizou_banheiro": None},
    "vestuario": {"colaborou_roupa": None, "incomodo_sensorial": None},
    "rotina": {"guardou_brinquedos": None, "ajudou_tarefa": None, "aceitou_transicao": None},
    "observacoes": {"conquistas": None, "dificuldades": None, "diferente_hoje": None}
}

CATEGORIAS_EVENTO = {"alimentacao", "comunicacao", "sono"}

def simular_persistencia(campos_novos):
    for categoria, dados in campos_novos.items():
        if not dados:
            continue
        
        # EVENTOS: cada item da lista vira uma linha nova no banco
        if categoria in CATEGORIAS_EVENTO:
            if isinstance(dados, list):
                for evento in dados:
                    evento_limpo = {k: v for k, v in evento.items() if v is not None}
                    if evento_limpo:
                        db_eventos[categoria].append(evento_limpo)
        
        # ACUMULATIVOS: UPSERT (COALESCE / array_cat / CONCAT_WS)
        elif categoria in db_acumulado:
            for chave, valor_novo in dados.items():
                if valor_novo is None:
                    continue
                valor_atual = db_acumulado[categoria].get(chave)
                
                if isinstance(valor_novo, list):
                    if valor_atual is None:
                        db_acumulado[categoria][chave] = []
                    db_acumulado[categoria][chave].extend(valor_novo)
                elif categoria == "observacoes":
                    if valor_atual is None:
                        db_acumulado[categoria][chave] = valor_novo
                    else:
                        db_acumulado[categoria][chave] = f"{valor_atual}\n{valor_novo}"
                else:
                    db_acumulado[categoria][chave] = valor_novo

# ============================================================
# EXECUÇÃO
# ============================================================

def rodar_teste():
    print("=== TESTE HÍBRIDO: EVENTOS + ACUMULATIVOS (SEQUENCIAL) ===\n")
    
    for i, mensagem in enumerate(mensagens_teste, 1):
        print(f"[{i}/{len(mensagens_teste)}] '{mensagem[:80]}{'...' if len(mensagem) > 80 else ''}'")

        try:
            response = client.beta.chat.completions.parse(
                model="gpt-4o-2024-08-06",
                messages=[
                    {"role": "system", "content": prompt_checklist},
                    {"role": "user", "content": mensagem}
                ],
                response_format=LLMChecklistResponseHibrido,
                temperature=0.0
            )
            
            resultado = response.choices[0].message.parsed
            
            if resultado.contem_dados and resultado.relatos:
                campos = resultado.relatos[0].campos_preenchidos.model_dump(exclude_none=True)
                simular_persistencia(campos)
                
        except Exception as e:
            print(f"  ERRO: {e}")

    # ---- EXIBIÇÃO DO RESULTADO FINAL ----
    
    print("\n" + "="*60)
    print("EVENTOS DE ALIMENTAÇÃO (cada linha = 1 registro no banco):")
    print("="*60)
    for i, ev in enumerate(db_eventos["alimentacao"], 1):
        print(f"  Evento {i}: {json.dumps(ev, ensure_ascii=False)}")
    
    print(f"\n{'='*60}")
    print("EVENTOS DE COMUNICAÇÃO:")
    print("="*60)
    for i, ev in enumerate(db_eventos["comunicacao"], 1):
        print(f"  Evento {i}: {json.dumps(ev, ensure_ascii=False)}")
    
    print(f"\n{'='*60}")
    print("EVENTOS DE SONO:")
    print("="*60)
    if db_eventos["sono"]:
        for i, ev in enumerate(db_eventos["sono"], 1):
            print(f"  Evento {i}: {json.dumps(ev, ensure_ascii=False)}")
    else:
        print("  (nenhum evento de sono neste teste)")
    
    print(f"\n{'='*60}")
    print("ACUMULATIVOS (resumo do dia):")
    print("="*60)
    db_final = {}
    for cat, campos in db_acumulado.items():
        campos_preenchidos = {k: v for k, v in campos.items() if v is not None and v != []}
        if campos_preenchidos:
            db_final[cat] = campos_preenchidos
    print(json.dumps(db_final, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    rodar_teste()
