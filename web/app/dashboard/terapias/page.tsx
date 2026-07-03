'use client'

import { useEffect, useState } from 'react'
import { Header } from '@/components/layout/Header'
import { getCriancaSelecionada } from '@/lib/auth'
import { apiFetch } from '@/lib/api'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

interface SessaoTerapia {
  id: string
  data: string
  horario_inicio?: string
  horario_fim?: string
  especialidade: string
  notas_sessao?: string
  nome_profissional?: string
}

export default function TerapiasPage() {
  const [criancaId] = useState(getCriancaSelecionada)
  const [terapias, setTerapias] = useState<SessaoTerapia[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingTerapia, setEditingTerapia] = useState<Partial<SessaoTerapia> | null>(null)

  const fetchTerapias = async () => {
    setLoading(true)
    try {
      const res: any = await apiFetch(`/api/terapias/${criancaId}`)
      setTerapias(res)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (criancaId) {
      fetchTerapias()
    }
  }, [criancaId])

  const openAddModal = () => {
    setEditingTerapia({
      data: new Date().toISOString().split('T')[0],
      especialidade: '',
      horario_inicio: '',
      horario_fim: '',
      notas_sessao: ''
    })
    setModalOpen(true)
  }

  const openEditModal = (t: SessaoTerapia) => {
    setEditingTerapia({ ...t })
    setModalOpen(true)
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Deseja realmente remover esta terapia?')) return
    try {
      await apiFetch(`/api/terapias/${criancaId}/${id}`, { method: 'DELETE' })
      fetchTerapias()
    } catch (e) {
      alert('Erro ao deletar')
    }
  }

  const handleSave = async () => {
    if (!editingTerapia?.data) return
    try {
      if (editingTerapia.id) {
        await apiFetch(`/api/terapias/${criancaId}/${editingTerapia.id}`, {
          method: 'PATCH',
          body: JSON.stringify(editingTerapia)
        })
      } else {
        await apiFetch(`/api/terapias/${criancaId}`, {
          method: 'POST',
          body: JSON.stringify(editingTerapia)
        })
      }
      setModalOpen(false)
      fetchTerapias()
    } catch (e) {
      alert('Erro ao salvar terapia')
    }
  }

  return (
    <>
      <Header titulo="Terapias" subtitulo="Acompanhamento clínico" />

      <div className="p-4 md:p-6 space-y-4">
        <div className="flex justify-end">
          <button 
            onClick={openAddModal}
            className="btn-primary text-sm py-2 px-4 shadow-sm hover:-translate-y-0.5 transition-transform"
          >
            + Nova Terapia
          </button>
        </div>

        {loading ? (
          <p className="text-manolo-muted">Carregando...</p>
        ) : terapias.length === 0 ? (
          <div className="card p-8 text-center text-manolo-muted">
            Nenhuma terapia registrada.
          </div>
        ) : (
          <div className="max-w-4xl space-y-4">
            {terapias.map(t => (
              <div key={t.id} className="card p-5 relative group">
                <div className="absolute top-4 right-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button onClick={() => openEditModal(t)} className="text-xs text-primary bg-primary-50 px-2 py-1 rounded">Editar</button>
                  <button onClick={() => handleDelete(t.id)} className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded">Excluir</button>
                </div>
                
                <div className="mb-2">
                  <span className="text-xs font-semibold uppercase text-primary">{t.especialidade}</span>
                  <p className="font-medium text-manolo-text mt-1">
                    {format(new Date(t.data + 'T12:00:00'), "EEEE, d 'de' MMMM", { locale: ptBR })}
                  </p>
                  <p className="text-xs text-manolo-muted mt-0.5">
                    {t.horario_inicio && t.horario_fim ? `${t.horario_inicio} - ${t.horario_fim}` : 'Horário não informado'}
                    {t.nome_profissional && ` • Por ${t.nome_profissional}`}
                  </p>
                </div>
                
                {t.notas_sessao && (
                  <div className="mt-4 pt-4 border-t border-neutral-border">
                    <p className="text-sm text-manolo-text whitespace-pre-line">{t.notas_sessao}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {modalOpen && editingTerapia && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={() => setModalOpen(false)} />
          <div className="relative card w-full max-w-md flex flex-col animate-slide-up p-5">
            <h2 className="text-lg font-semibold text-manolo-text mb-4">
              {editingTerapia.id ? 'Editar Terapia' : 'Nova Terapia'}
            </h2>
            
            <div className="space-y-4">
              <div>
                <label className="label">Data</label>
                <input type="date" className="input" value={editingTerapia.data || ''} onChange={e => setEditingTerapia({ ...editingTerapia, data: e.target.value })} />
              </div>
              <div>
                <label className="label">Especialidade</label>
                <input type="text" className="input" placeholder="Ex: Fonoaudiologia" value={editingTerapia.especialidade || ''} onChange={e => setEditingTerapia({ ...editingTerapia, especialidade: e.target.value })} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">Início</label>
                  <input type="time" className="input" value={editingTerapia.horario_inicio || ''} onChange={e => setEditingTerapia({ ...editingTerapia, horario_inicio: e.target.value })} />
                </div>
                <div>
                  <label className="label">Fim</label>
                  <input type="time" className="input" value={editingTerapia.horario_fim || ''} onChange={e => setEditingTerapia({ ...editingTerapia, horario_fim: e.target.value })} />
                </div>
              </div>
              <div>
                <label className="label">Notas da Sessão</label>
                <textarea className="input min-h-[240px]" value={editingTerapia.notas_sessao || ''} onChange={e => setEditingTerapia({ ...editingTerapia, notas_sessao: e.target.value })}></textarea>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button onClick={() => setModalOpen(false)} className="btn-ghost">Cancelar</button>
              <button onClick={handleSave} className="btn-primary px-6">Salvar</button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
