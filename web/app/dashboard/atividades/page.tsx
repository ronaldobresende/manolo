'use client'

import { useEffect, useState } from 'react'
import { Header } from '@/components/layout/Header'
import { getAtividades, criarAtividade, atualizarStatusAtividade } from '@/lib/api'
import { getCriancaSelecionada } from '@/lib/auth'
import type { Atividade, StatusAtividade, TipoAtividade } from '@/types/manolo'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import clsx from 'clsx'

// ============================================================
// HELPERS
// ============================================================

const STATUS_CONFIG: Record<StatusAtividade, { label: string; classe: string }> = {
  pendente:      { label: 'Pendente',      classe: 'badge-gray' },
  em_andamento:  { label: 'Em andamento',  classe: 'badge-yellow' },
  concluida:     { label: 'Concluída',     classe: 'badge-green' },
}

const TIPOS_ATIVIDADE: TipoAtividade[] = [
  'brincadeira', 'alimentacao', 'comunicacao', 'motor', 'higiene', 'rotina',
]

const TIPO_EMOJI: Record<TipoAtividade, string> = {
  brincadeira: '🎮', alimentacao: '🍽️', comunicacao: '💬',
  motor: '🤸', higiene: '🚿', rotina: '📋',
}

// ============================================================
// CARD DE ATIVIDADE
// ============================================================

interface CardAtividadeProps {
  atividade: Atividade
  criancaId: string
  onStatusUpdate: (id: string, novoStatus: StatusAtividade, feedback?: string) => void
}

function CardAtividade({ atividade: a, criancaId, onStatusUpdate }: CardAtividadeProps) {
  const [expandido, setExpandido] = useState(false)
  const [feedback, setFeedback] = useState(a.feedback || '')
  const [atualizando, setAtualizando] = useState(false)

  const handleStatus = async (novoStatus: StatusAtividade) => {
    setAtualizando(true)
    try {
      await atualizarStatusAtividade(a.id, { status: novoStatus, feedback, crianca_id: criancaId })
      onStatusUpdate(a.id, novoStatus, feedback)
    } catch {
    } finally {
      setAtualizando(false)
    }
  }

  const cfg = STATUS_CONFIG[a.status]

  return (
    <div className="card p-5 animate-fade-in">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <span className="text-2xl flex-shrink-0">{TIPO_EMOJI[a.tipo]}</span>
          <div className="min-w-0">
            <h3 className="font-medium text-manolo-text text-sm leading-snug">{a.titulo}</h3>
            {a.objetivo && <p className="text-xs text-manolo-muted mt-0.5 truncate">{a.objetivo}</p>}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className={`badge ${cfg.classe}`}>{cfg.label}</span>
          <button
            onClick={() => setExpandido(!expandido)}
            className="btn-ghost p-1 text-xs"
          >
            {expandido ? '▲' : '▼'}
          </button>
        </div>
      </div>

      {expandido && (
        <div className="mt-4 space-y-3 border-t border-neutral-border pt-4 animate-fade-in">
          <p className="text-sm text-manolo-text">{a.descricao}</p>

          {a.materiais && a.materiais.length > 0 && (
            <div>
              <span className="label">Materiais</span>
              <p className="text-sm text-manolo-muted">{a.materiais.join(', ')}</p>
            </div>
          )}

          {a.duracao_minutos && (
            <p className="text-xs text-manolo-muted">⏱ {a.duracao_minutos} minutos</p>
          )}

          {/* Feedback */}
          <div>
            <label className="label">Feedback da família</label>
            <textarea
              className="input resize-none"
              rows={2}
              value={feedback}
              onChange={e => setFeedback(e.target.value)}
              placeholder="Como foi essa atividade?"
            />
          </div>

          {/* Ações de status */}
          <div className="flex flex-wrap gap-2">
            {(['pendente', 'em_andamento', 'concluida'] as StatusAtividade[]).map(s => (
              <button
                key={s}
                disabled={a.status === s || atualizando}
                onClick={() => handleStatus(s)}
                className={clsx(
                  'text-xs py-1.5 px-3 rounded-lg transition-all',
                  a.status === s
                    ? 'bg-primary-100 text-primary font-medium cursor-default'
                    : 'btn-secondary'
                )}
              >
                {STATUS_CONFIG[s].label}
              </button>
            ))}
          </div>

          <p className="text-xs text-manolo-muted">
            Recomendada em {format(new Date(a.data_recomendacao + 'T12:00:00'), "d/MM/yyyy")}
            {a.criada_por_nome && ` · ${a.criada_por_nome}`}
          </p>
        </div>
      )}
    </div>
  )
}

// ============================================================
// FORMULÁRIO DE NOVA ATIVIDADE
// ============================================================

interface FormAtividadeProps {
  criancaId: string
  onCriada: (a: Atividade) => void
}

function FormAtividade({ criancaId, onCriada }: FormAtividadeProps) {
  const [open, setOpen] = useState(false)
  const [titulo, setTitulo] = useState('')
  const [descricao, setDescricao] = useState('')
  const [tipo, setTipo] = useState<TipoAtividade>('brincadeira')
  const [objetivo, setObjetivo] = useState('')
  const [materiais, setMateriais] = useState('')
  const [duracao, setDuracao] = useState('')
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!titulo || !descricao) { setErro('Título e descrição são obrigatórios.'); return }
    setSalvando(true); setErro(null)
    try {
      const nova = await criarAtividade({
        titulo, descricao, tipo, objetivo: objetivo || undefined,
        materiais: materiais ? materiais.split(',').map(m => m.trim()) : undefined,
        duracao_minutos: duracao ? parseInt(duracao) : undefined,
        crianca_id: criancaId,
      })
      onCriada({ ...nova, status: 'pendente', data_recomendacao: format(new Date(), 'yyyy-MM-dd') })
      setOpen(false)
      setTitulo(''); setDescricao(''); setObjetivo(''); setMateriais(''); setDuracao('')
    } catch (e: unknown) {
      setErro(e instanceof Error ? e.message : 'Erro ao salvar.')
    } finally {
      setSalvando(false)
    }
  }

  if (!open) return <button className="btn-primary" onClick={() => setOpen(true)}>+ Nova atividade</button>

  return (
    <div className="card p-5 animate-slide-up">
      <div className="flex items-center justify-between mb-4">
        <h3 className="section-title">Nova atividade</h3>
        <button className="btn-ghost text-xs" onClick={() => setOpen(false)}>Cancelar</button>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <label className="label">Título *</label>
            <input className="input" value={titulo} onChange={e => setTitulo(e.target.value)} placeholder="Ex: Brincadeira com blocos coloridos" />
          </div>
          <div>
            <label className="label">Tipo *</label>
            <select className="select" value={tipo} onChange={e => setTipo(e.target.value as TipoAtividade)}>
              {TIPOS_ATIVIDADE.map(t => <option key={t} value={t}>{TIPO_EMOJI[t]} {t}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Duração (minutos)</label>
            <input type="number" className="input" value={duracao} onChange={e => setDuracao(e.target.value)} placeholder="15" />
          </div>
          <div className="sm:col-span-2">
            <label className="label">Descrição *</label>
            <textarea className="input resize-none" rows={3} value={descricao} onChange={e => setDescricao(e.target.value)} placeholder="Como executar a atividade..." />
          </div>
          <div className="sm:col-span-2">
            <label className="label">Objetivo terapêutico</label>
            <input className="input" value={objetivo} onChange={e => setObjetivo(e.target.value)} placeholder="Ex: Estimular atenção compartilhada" />
          </div>
          <div className="sm:col-span-2">
            <label className="label">Materiais (separados por vírgula)</label>
            <input className="input" value={materiais} onChange={e => setMateriais(e.target.value)} placeholder="Ex: blocos, tapete, espelho" />
          </div>
        </div>
        {erro && <p className="text-sm text-manolo-danger">{erro}</p>}
        <button type="submit" disabled={salvando} className="btn-primary">
          {salvando ? 'Salvando...' : 'Criar atividade'}
        </button>
      </form>
    </div>
  )
}

// ============================================================
// PÁGINA
// ============================================================

export default function AtividadesPage() {
  const [atividades, setAtividades] = useState<Atividade[]>([])
  const [loading, setLoading] = useState(true)
  const [filtroStatus, setFiltroStatus] = useState<StatusAtividade | 'todas'>('todas')
  const [criancaId] = useState(getCriancaSelecionada)

  useEffect(() => {
    getAtividades(criancaId)
      .then(setAtividades)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [criancaId])

  const filtradas = filtroStatus === 'todas'
    ? atividades
    : atividades.filter(a => a.status === filtroStatus)

  const handleStatusUpdate = (id: string, novoStatus: StatusAtividade, feedback?: string) => {
    setAtividades(prev => prev.map(a =>
      a.id === id ? { ...a, status: novoStatus, feedback: feedback ?? a.feedback } : a
    ))
  }

  return (
    <>
      <Header titulo="Atividades" subtitulo="Propostas pelos terapeutas" />

      <div className="p-4 md:p-6 space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Filtro de status */}
          <div className="flex gap-2 flex-wrap">
            {(['todas', 'pendente', 'em_andamento', 'concluida'] as const).map(s => (
              <button
                key={s}
                onClick={() => setFiltroStatus(s)}
                className={filtroStatus === s ? 'btn-primary py-1.5 px-3 text-xs' : 'btn-secondary py-1.5 px-3 text-xs'}
              >
                {s === 'todas' ? 'Todas' : STATUS_CONFIG[s].label}
              </button>
            ))}
          </div>
          <FormAtividade criancaId={criancaId} onCriada={a => setAtividades(prev => [a, ...prev])} />
        </div>

        {loading && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[...Array(4)].map((_, i) => <div key={i} className="skeleton h-24 rounded-card" />)}
          </div>
        )}

        {!loading && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {filtradas.map(a => (
              <CardAtividade
                key={a.id}
                atividade={a}
                criancaId={criancaId}
                onStatusUpdate={handleStatusUpdate}
              />
            ))}
            {filtradas.length === 0 && (
              <div className="sm:col-span-2 card p-8 text-center text-manolo-muted text-sm">
                Nenhuma atividade {filtroStatus === 'todas' ? '' : `com status "${filtroStatus}"`} encontrada.
              </div>
            )}
          </div>
        )}
      </div>
    </>
  )
}
