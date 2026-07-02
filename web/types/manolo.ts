/**
 * Tipos TypeScript do projeto Manolo — Web App Fase 4.
 * Espelham o modelo de dados PostgreSQL definido em MANOLO.md § 4.
 */

// ============================================================
// ENTIDADES BASE
// ============================================================

export interface Crianca {
  id: string
  account_id: string
  nome: string
  data_nascimento: string // ISO date string
  diagnosticos: string[]
  foto_url?: string
  criado_em: string
}

export interface Usuario {
  id: string
  account_id: string
  nome: string
  telefone_whatsapp: string
  email?: string
  perfil: 'admin' | 'família' | 'terapeuta'
  ativo: boolean
  criado_em: string
}

// ============================================================
// PERFIL VIVO
// ============================================================

export interface PerfilComunicacao {
  gestos?: string
  palavras_ativas?: string[]
  combinacao_gesto_palavra?: boolean
  puxar_mao?: string
  respondeu_nome?: string
}

export interface PerfilMotor {
  grosso?: string
  fino?: string
}

export interface PerfilAlimentacao {
  aceita_bem?: string[]
  recusa_frequente?: string[]
  utensilio?: string
}

export interface PerfilSono {
  media_horas?: number
  acorda_noite?: string
}

export interface PerfilRegulacao {
  gatilhos_crise?: string[]
  o_que_acalma?: string[]
}

export interface PerfilVivo {
  id: string
  crianca_id: string
  nome_crianca: string
  data_nascimento: string
  atualizado_em: string
  comunicacao: PerfilComunicacao
  motor: PerfilMotor
  alimentacao: PerfilAlimentacao
  sono: PerfilSono
  regulacao: PerfilRegulacao
  resumo_geral: string
}

// ============================================================
// CHECKLISTS
// ============================================================

export type ResumoDia = 'muito_bom' | 'bom' | 'regular' | 'difícil'
export type OrigemChecklist = 'whatsapp_audio' | 'whatsapp_video' | 'whatsapp_texto' | 'web' | 'terminal'

export interface ChecklistResumo {
  id: string
  data: string
  resumo_dia?: ResumoDia
  origem?: OrigemChecklist
  criado_em: string
  // Campos de join para a listagem
  dormiu_as?: string
  acordou_as?: string
  acordou_noite?: boolean
  cochilo_inicio?: string
  cochilo_fim?: string
  humor_geral?: string
  teve_crise?: boolean
  palavras_ditas?: string[]
  usou_gestos?: boolean
  respondeu_nome?: string
  comeu_bem?: boolean
  utensilio?: string
  tempo_sem_tela_minutos?: number
  modo_brincar?: string
  usou_tela?: boolean
  tempo_tela_minutos?: number
}

export interface SecaoSono {
  dormiu_as?: string
  acordou_as?: string
  acordou_noite?: boolean
  cochilo_inicio?: string
  cochilo_fim?: string
  notas?: string
}

export interface SecaoTela {
  usou_tela?: boolean
  tempo_minutos?: number
  conteudo?: string
  reacao_retirada?: 'tranquilo' | 'resistencia' | 'crise'
}

export interface SecaoAlimentacao {
  comeu_bem?: boolean
  aceitou?: string[]
  recusou?: string[]
  comeu_sentado?: boolean
  utensilio?: 'colher' | 'garfo' | 'mao' | 'misto'
}

export interface SecaoComunicacao {
  usou_gestos?: boolean
  palavras_ditas?: string[]
  apontou?: boolean
  puxou_mao?: 'nunca' | 'às_vezes' | 'maioria' | 'sempre'
  respondeu_nome?: 'nunca' | 'às_vezes' | 'sempre'
  imitou?: boolean
}

export interface SecaoBrincar {
  com_que_brincou?: string[]
  modo?: 'sozinho' | 'com_adulto' | 'misto'
  fez_faz_de_conta?: boolean
  tempo_sem_tela_minutos?: number
}

export interface SecaoHigiene {
  banho?: 'tranquilo' | 'resistencia' | 'crise'
  escovou_dentes?: boolean
  sinalizou_banheiro?: boolean
}

export interface SecaoVestuario {
  colaborou_roupa?: boolean
  incomodo_sensorial?: boolean
}

export interface SecaoMovimento {
  atividades?: string[]
  caiu_muito?: boolean
  buscou_colo?: boolean
}

export interface SecaoHumor {
  humor_geral?: 'muito_bom' | 'bom' | 'regular' | 'agitado' | 'difícil'
  teve_crise?: boolean
  o_que_acalmou?: string
  notas?: string
}

export interface SecaoRotina {
  guardou_brinquedos?: boolean
  ajudou_tarefa?: boolean
  aceitou_transicao?: boolean
}

export interface SecaoObservacoes {
  conquistas?: string
  dificuldades?: string
  diferente_hoje?: string
}

export interface ChecklistDetalhado {
  id: string
  data: string
  resumo_dia?: ResumoDia
  origem?: OrigemChecklist
  criado_em: string
  secoes: {
    sono?: SecaoSono | null
    tela?: SecaoTela | null
    alimentacao?: SecaoAlimentacao | null
    comunicacao?: SecaoComunicacao | null
    brincar?: SecaoBrincar | null
    higiene?: SecaoHigiene | null
    vestuario?: SecaoVestuario | null
    movimento?: SecaoMovimento | null
    humor?: SecaoHumor | null
    rotina?: SecaoRotina | null
    observacoes?: SecaoObservacoes | null
  }
}

export interface ChecklistsResponse {
  total: number
  pagina: number
  por_pagina: number
  checklists: ChecklistResumo[]
}

// ============================================================
// DOCUMENTOS
// ============================================================

export type TipoDocumento = 'laudo' | 'relatorio_sessao' | 'avaliacao' | 'receita' | 'outro'

export interface Documento {
  id: string
  tipo: TipoDocumento
  especialidade?: string
  titulo: string
  data_documento?: string
  storage_path?: string
  processado: boolean
  criado_em: string
}

// ============================================================
// MARCOS
// ============================================================

export interface Marco {
  id: string
  descricao: string
  data_marco: string
  criado_em: string
  registrado_por?: string
}

// ============================================================
// ATIVIDADES
// ============================================================

export type TipoAtividade = 'brincadeira' | 'alimentacao' | 'comunicacao' | 'motor' | 'higiene' | 'rotina'
export type StatusAtividade = 'pendente' | 'em_andamento' | 'concluida'

export interface Atividade {
  id: string
  titulo: string
  descricao: string
  tipo: TipoAtividade
  objetivo?: string
  materiais?: string[]
  duracao_minutos?: number
  criado_em: string
  criada_por_nome?: string
  status: StatusAtividade
  feedback?: string
  data_recomendacao: string
}

// ============================================================
// CHAT
// ============================================================

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

// ============================================================
// GRÁFICOS / EVOLUÇÃO
// ============================================================

export type PeriodoFiltro = '7d' | '30d' | '90d' | 'custom'

export interface DadoEvolucaoSono {
  data: string
  horas_dormidas?: number
  acordou_noite?: boolean
}

export interface DadoEvolucaoComunicacao {
  data: string
  num_palavras?: number
  usou_gestos?: boolean
  respondeu_nome?: string
}

export interface DadoEvolucaoHumor {
  data: string
  teve_crise?: boolean
  humor_geral?: string
}

export interface DadoEvolucaoAlimentacao {
  data: string
  comeu_bem?: boolean
  utensilio?: string
}

export interface DadoEvolucaoBrincar {
  data: string
  tempo_sem_tela?: number
  modo?: string
}
