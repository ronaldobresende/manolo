"""Modelos Pydantic para validação de dados estruturados."""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# ==========================================
# Sub-modelos do Checklist Diário
# ==========================================

class SonoModel(BaseModel):
    dormiu_as: Optional[str] = Field(None, description="Horário aproximado em que dormiu (formato HH:MM)")
    acordou_as: Optional[str] = Field(None, description="Horário aproximado em que acordou (formato HH:MM)")
    acordou_noite: Optional[bool] = Field(None, description="Indica se a criança acordou durante a noite")
    cochilo_inicio: Optional[str] = Field(None, description="Horário aproximado em que iniciou o cochilo da tarde (formato HH:MM)")
    cochilo_fim: Optional[str] = Field(None, description="Horário aproximado em que acordou do cochilo da tarde (formato HH:MM)")
    notas: Optional[str] = Field(None, description="Notas adicionais ou observações livres sobre o sono e rotina noturna")

class TelaModel(BaseModel):
    usou_tela: Optional[bool] = Field(None, description="Se a criança usou telas (celular, TV, tablet, etc.)")
    tempo_minutos: Optional[int] = Field(None, description="Tempo total de uso de tela em minutos")
    conteudo: Optional[str] = Field(None, description="O que a criança assistiu ou jogou")
    reacao_retirada: Optional[Literal['tranquilo', 'resistencia', 'crise']] = Field(None, description="Reação da criança ao retirar a tela")

class AlimentacaoModel(BaseModel):
    comeu_bem: Optional[bool] = Field(None, description="Se a criança comeu bem nas refeições")
    aceitou: Optional[List[str]] = Field(None, description="Quais alimentos foram aceitos. Inclua explicitamente mamadeiras, líquidos, água, lanches e qualquer refeição. Inclua o horário se mencionado (ex: 'mamadeira às 15:00', 'maçã de manhã').")
    recusou: Optional[List[str]] = Field(None, description="Quais alimentos foram recusados (ex: 'recusou arroz no almoço')")
    comeu_sentado: Optional[bool] = Field(None, description="Se comeu sentado à mesa ou cadeirão")
    utensilio: Optional[Literal['colher', 'garfo', 'mao', 'misto']] = Field(None, description="Qual utensílio usou para comer")

class ComunicacaoModel(BaseModel):
    usou_gestos: Optional[bool] = Field(None, description="Se usou gestos para se comunicar")
    palavras_ditas: Optional[List[str]] = Field(None, description="Lista de palavras ditas no dia. Sons com intenção de fala e aproximações (ex: 'dadada', 'keka', 'doog') TAMBÉM contam como palavras.")
    apontou: Optional[bool] = Field(None, description="Se apontou para os objetos desejados")
    puxou_mao: Optional[Literal['nunca', 'às_vezes', 'maioria', 'sempre']] = Field(None, description="Frequência com que puxou a mão de um adulto")
    respondeu_nome: Optional[Literal['nunca', 'às_vezes', 'sempre']] = Field(None, description="Se respondeu/atendeu ao ser chamada pelo nome")
    imitou: Optional[bool] = Field(None, description="Se imitou gestos ou sons dos outros")

class BrincarModel(BaseModel):
    com_que_brincou: Optional[List[str]] = Field(None, description="Quais brinquedos ou atividades. Inclua o contexto se mencionado (ex: 'brincou de carrinho de manhã', 'brincou na areia').")
    modo: Optional[Literal['sozinho', 'com_adulto', 'misto']] = Field(None, description="Como brincou")
    fez_faz_de_conta: Optional[bool] = Field(None, description="Se fez brincadeira de faz-de-conta ou simbólica (ex: fazer casquinha, comidinha, imitar adultos ou situações reais)")
    tempo_sem_tela_minutos: Optional[int] = Field(None, description="Tempo estimado de brincadeira sem telas")

class HigieneModel(BaseModel):
    banho: Optional[Literal['tranquilo', 'resistencia', 'crise']] = Field(None, description="Como foi o banho")
    escovou_dentes: Optional[bool] = Field(None, description="Se escovou os dentes")
    sinalizou_banheiro: Optional[bool] = Field(None, description="Se pediu para ir ao banheiro ou usar o penico")

class VestuarioModel(BaseModel):
    colaborou_roupa: Optional[bool] = Field(None, description="Se ajudou ou deixou vestir a roupa tranquilamente")
    incomodo_sensorial: Optional[bool] = Field(None, description="Se demonstrou incômodo com etiquetas, texturas ou sapatos")

class MovimentoModel(BaseModel):
    atividades: Optional[List[str]] = Field(None, description="Atividades físicas ou interações motoras com o ambiente (ex: 'correu no parque à tarde', 'subiu e desceu do sofá', 'pular')")
    caiu_muito: Optional[bool] = Field(None, description="Se tropeçou ou caiu frequentemente")
    buscou_colo: Optional[bool] = Field(None, description="Se pediu colo excessivamente")

class HumorModel(BaseModel):
    humor_geral: Optional[Literal['muito_bom', 'bom', 'regular', 'agitado', 'difícil']] = Field(None, description="Estado de humor predominante no dia")
    teve_crise: Optional[bool] = Field(None, description="Se teve crises de choro, birra intensa ou desregulação")
    o_que_acalmou: Optional[str] = Field(None, description="O que ajudou a acalmar a criança após um momento difícil")
    notas: Optional[str] = Field(None, description="Notas extras ou relato subjetivo sobre o humor e comportamento")

class RotinaModel(BaseModel):
    guardou_brinquedos: Optional[bool] = Field(None, description="Se ajudou a guardar os brinquedos")
    ajudou_tarefa: Optional[bool] = Field(None, description="Se participou ou ajudou em alguma tarefa da casa")
    aceitou_transicao: Optional[bool] = Field(None, description="Se aceitou de forma tranquila as transições entre atividades")

class ObservacoesModel(BaseModel):
    conquistas: Optional[str] = Field(None, description="Avanços de autonomia, iniciativa funcional, marcos ou comportamentos positivos (ex: 'foi na bolsa e pegou chocolate sozinho'). NÃO coloque aqui o que ele comeu ou brincou se couber nos campos específicos.")
    dificuldades: Optional[str] = Field(None, description="Desafios, frustrações ou birras que não couberam nos campos específicos.")
    diferente_hoje: Optional[str] = Field(None, description="Qualquer outra observação qualitativa ou contextual.")

class CamposPreenchidos(BaseModel):
    sono: Optional[SonoModel] = None
    humor: Optional[HumorModel] = None
    comunicacao: Optional[ComunicacaoModel] = None
    alimentacao: Optional[AlimentacaoModel] = None
    brincar: Optional[BrincarModel] = None
    higiene: Optional[HigieneModel] = None
    movimento: Optional[MovimentoModel] = None
    vestuario: Optional[VestuarioModel] = None
    tela: Optional[TelaModel] = None
    rotina: Optional[RotinaModel] = None
    observacoes: Optional[ObservacoesModel] = None

class RelatoDiario(BaseModel):
    data_referencia_iso: Optional[str] = Field(None, description="Data à qual o relato se refere, no formato YYYY-MM-DD. NUNCA infira 'ontem' ou outras datas. Se o usuário NÃO disser a data (ex: 'ele dormiu mal'), retorne null para que o sistema assuma HOJE.")
    campos_preenchidos: CamposPreenchidos = Field(default_factory=CamposPreenchidos)

class LLMChecklistResponse(BaseModel):
    """Modelo principal que envolve todos os campos detectados na mensagem."""
    contem_dados: bool = Field(description="Indica se a mensagem do usuário contêm QUALQUER informação sobre a rotina/dia a dia da criança.")
    data_ambigua: bool = Field(False, description="True se o usuário mencionou um dia muito vago (ex: 'ontem', 'terça') MAS O CONTEXTO AINDA É DUVIDOSO, ou se disse 'uma refeição' sem especificar qual. Em caso de dúvida sobre a data ou contexto, marque como True.")
    correcao_retroativa: bool = Field(False, description="True se o usuário estiver explicitamente corrigindo a data de relatos recém-enviados (ex: 'errei, aquilo não era pra hoje, era de ontem').")
    data_destino_correcao: Optional[str] = Field(None, description="Se correcao_retroativa for True, preencha a data ISO correta para a qual os dados devem ser movidos.")
    relatos: List[RelatoDiario] = Field(default_factory=list, description="Lista de relatos diários extraídos da mensagem.")
    campos_ausentes: List[str] = Field(default_factory=list, description="Lista apenas as categorias (ex: 'sono', 'alimentacao') que NÃO foram mencionadas de forma alguma na mensagem.")