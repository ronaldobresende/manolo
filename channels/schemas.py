from typing import Optional, List
from pydantic import BaseModel, Field

class ChecklistSono(BaseModel):
    dormiu_as: Optional[str] = None
    acordou_as: Optional[str] = None
    acordou_noite: Optional[bool] = None
    cochilo_inicio: Optional[str] = None
    cochilo_fim: Optional[str] = None
    notas: Optional[str] = None

class ChecklistTela(BaseModel):
    usou_tela: Optional[bool] = None
    tempo_minutos: Optional[int] = None
    conteudo: Optional[str] = None
    reacao_retirada: Optional[str] = None

class ChecklistAlimentacao(BaseModel):
    comeu_bem: Optional[bool] = None
    aceitou: Optional[List[str]] = Field(default_factory=list)
    recusou: Optional[List[str]] = Field(default_factory=list)
    comeu_sentado: Optional[bool] = None
    utensilio: Optional[str] = None

class ChecklistComunicacao(BaseModel):
    usou_gestos: Optional[bool] = None
    palavras_ditas: Optional[List[str]] = Field(default_factory=list)
    apontou: Optional[bool] = None
    puxou_mao: Optional[str] = None
    respondeu_nome: Optional[str] = None
    imitou: Optional[bool] = None

class ChecklistBrincar(BaseModel):
    com_que_brincou: Optional[List[str]] = Field(default_factory=list)
    modo: Optional[str] = None
    fez_faz_de_conta: Optional[bool] = None
    tempo_sem_tela_minutos: Optional[int] = None

class ChecklistHigiene(BaseModel):
    banho: Optional[str] = None
    escovou_dentes: Optional[bool] = None
    sinalizou_banheiro: Optional[bool] = None

class ChecklistVestuario(BaseModel):
    colaborou_roupa: Optional[bool] = None
    incomodo_sensorial: Optional[bool] = None

class ChecklistMovimento(BaseModel):
    atividades: Optional[List[str]] = Field(default_factory=list)
    caiu_muito: Optional[bool] = None
    buscou_colo: Optional[bool] = None

class ChecklistHumor(BaseModel):
    humor_geral: Optional[str] = None
    teve_crise: Optional[bool] = None
    o_que_acalmou: Optional[str] = None
    cobertor_disponivel: Optional[bool] = None
    se_acalmou_sem_cobertor: Optional[bool] = None
    notas: Optional[str] = None

class ChecklistRotina(BaseModel):
    guardou_brinquedos: Optional[bool] = None
    ajudou_tarefa: Optional[bool] = None
    aceitou_transicao: Optional[bool] = None
    teve_escola: Optional[bool] = None

class ChecklistObservacoes(BaseModel):
    conquistas: Optional[str] = None
    dificuldades: Optional[str] = None
    diferente_hoje: Optional[str] = None

class SessaoTerapia(BaseModel):
    id: Optional[str] = None
    horario_inicio: Optional[str] = None
    horario_fim: Optional[str] = None
    especialidade: Optional[str] = None
    notas_sessao: Optional[str] = None

class ChecklistPayload(BaseModel):
    data: str
    resumo_dia: Optional[str] = None
    sono: Optional[ChecklistSono] = None
    tela: Optional[ChecklistTela] = None
    alimentacao: Optional[ChecklistAlimentacao] = None
    comunicacao: Optional[ChecklistComunicacao] = None
    brincar: Optional[ChecklistBrincar] = None
    higiene: Optional[ChecklistHigiene] = None
    vestuario: Optional[ChecklistVestuario] = None
    movimento: Optional[ChecklistMovimento] = None
    humor: Optional[ChecklistHumor] = None
    rotina: Optional[ChecklistRotina] = None
    observacoes: Optional[ChecklistObservacoes] = None
    sessoes_terapia: Optional[List[SessaoTerapia]] = Field(default_factory=list)
