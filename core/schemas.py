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
    cochilo: Optional[bool] = Field(None, description="Se fez cochilos durante o dia")
    notas: Optional[str] = Field(None, description="Notas adicionais ou observações livres sobre o sono e rotina noturna")

class TelaModel(BaseModel):
    usou_tela: Optional[bool] = Field(None, description="Se a criança usou telas (celular, TV, tablet, etc.)")
    tempo_minutos: Optional[int] = Field(None, description="Tempo total de uso de tela em minutos")
    conteudo: Optional[str] = Field(None, description="O que a criança assistiu ou jogou")
    reacao_retirada: Optional[Literal['tranquilo', 'resistencia', 'crise']] = Field(None, description="Reação da criança ao retirar a tela")

class AlimentacaoModel(BaseModel):
    comeu_bem: Optional[bool] = Field(None, description="Se a criança comeu bem nas refeições")
    aceitou: Optional[List[str]] = Field(None, description="Quais alimentos foram aceitos")
    recusou: Optional[List[str]] = Field(None, description="Quais alimentos foram recusados")
    comeu_sentado: Optional[bool] = Field(None, description="Se comeu sentado à mesa ou cadeirão")
    utensilio: Optional[Literal['colher', 'garfo', 'mao', 'misto']] = Field(None, description="Qual utensílio usou para comer")

class ComunicacaoModel(BaseModel):
    usou_gestos: Optional[bool] = Field(None, description="Se usou gestos para se comunicar")
    palavras_ditas: Optional[List[str]] = Field(None, description="Lista de palavras ditas no dia")
    apontou: Optional[bool] = Field(None, description="Se apontou para os objetos desejados")
    puxou_mao: Optional[Literal['nunca', 'às_vezes', 'maioria', 'sempre']] = Field(None, description="Frequência com que puxou a mão de um adulto")
    respondeu_nome: Optional[Literal['nunca', 'às_vezes', 'sempre']] = Field(None, description="Se respondeu/atendeu ao ser chamada pelo nome")
    imitou: Optional[bool] = Field(None, description="Se imitou gestos ou sons dos outros")

class BrincarModel(BaseModel):
    com_que_brincou: Optional[List[str]] = Field(None, description="Brinquedos ou objetos utilizados para brincar")
    modo: Optional[Literal['sozinho', 'com_adulto', 'misto']] = Field(None, description="Modo de interação durante a brincadeira")
    fez_faz_de_conta: Optional[bool] = Field(None, description="Se fez brincadeira de faz-de-conta (jogo simbólico)")
    tempo_sem_tela_minutos: Optional[int] = Field(None, description="Tempo que passou brincando ativamente sem telas")

class HigieneModel(BaseModel):
    banho: Optional[Literal['tranquilo', 'resistencia', 'crise']] = Field(None, description="Como foi o momento do banho")
    escovou_dentes: Optional[bool] = Field(None, description="Se escovou os dentes")
    sinalizou_banheiro: Optional[bool] = Field(None, description="Se avisou que queria ir ao banheiro ou fez xixi/cocô corretamente")

class VestuarioModel(BaseModel):
    colaborou_roupa: Optional[bool] = Field(None, description="Se colaborou/ajudou na hora de vestir a roupa")
    incomodo_sensorial: Optional[bool] = Field(None, description="Se demonstrou incômodo com tecidos, texturas ou etiquetas")

class MovimentoModel(BaseModel):
    atividades: Optional[List[str]] = Field(None, description="Atividades físicas ou de movimento realizadas (ex: nadar, correr)")
    caiu_muito: Optional[bool] = Field(None, description="Se caiu muito ou teve desequilíbrio")
    buscou_colo: Optional[bool] = Field(None, description="Se buscou muito o colo do adulto ao longo do dia")

class HumorModel(BaseModel):
    humor_geral: Optional[Literal['muito_bom', 'bom', 'regular', 'agitado', 'difícil']] = Field(None, description="Estado de humor predominante no dia")
    teve_crise: Optional[bool] = Field(None, description="Se teve crises de choro, birra intensa ou desregulação")
    o_que_acalmou: Optional[str] = Field(None, description="O que ajudou a acalmar a criança após um momento difícil")
    notas: Optional[str] = Field(None, description="Notas extras ou relato subjetivo sobre o humor e comportamento")

class RotinaModel(BaseModel):
    guardou_brinquedos: Optional[bool] = Field(None, description="Se guardou os brinquedos ou colaborou na organização")
    ajudou_tarefa: Optional[bool] = Field(None, description="Se participou ou ajudou em alguma tarefa da casa")
    aceitou_transicao: Optional[bool] = Field(None, description="Se aceitou de forma tranquila as transições entre atividades")

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

class LLMChecklistResponse(BaseModel):
    """Modelo principal que envolve todos os campos detectados na mensagem."""
    contem_dados: bool = Field(description="Indica se a mensagem do usuário contêm QUALQUER informação sobre a rotina/dia a dia da criança.")
    data_referencia_iso: Optional[str] = Field(None, description="Data à qual o relato se refere, no formato YYYY-MM-DD. Se a mensagem diz 'ontem', calcule a data baseada em {data_hoje}. Se não houver indicativo que é outro dia, use {data_hoje}.")
    campos_preenchidos: CamposPreenchidos = Field(default_factory=CamposPreenchidos)
    campos_ausentes: List[str] = Field(default_factory=list, description="Lista apenas as categorias (ex: 'sono', 'alimentacao') que NÃO foram mencionadas de forma alguma na mensagem.")