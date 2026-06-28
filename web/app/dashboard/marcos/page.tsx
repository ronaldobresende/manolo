'use client'

import { useEffect, useState } from 'react'
import { Header } from '@/components/layout/Header'
import { getMarcos, criarMarco } from '@/lib/api'
import { getCriancaSelecionada } from '@/lib/auth'
import type { Marco } from '@/types/manolo'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

export default function MarcosPage() {
  const [marcos, setMarcos] = useState<Marco[]>([])
  const [loading, setLoading] = useState(true)
  const [descricao, setDescricao] = useState('')
  const [dataMarco, setDataMarco] = useState(format(new Date(), 'yyyy-MM-dd'))
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [criancaId] = useState(getCriancaSelecionada)

  useEffect(() => {
    getMarcos(criancaId)
      .then(setMarcos)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [criancaId])

  const handleCriar = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!descricao) return
    setSalvando(true); setErro(null)
    try {
      const novo = await criarMarco(criancaId, { descricao, data_marco: dataMarco })
      setMarcos(prev => [novo, ...prev])
      setDescricao('')
    } catch (e: unknown) {
      setErro(e instanceof Error ? e.message : 'Erro ao salvar.')
    } finally {
      setSalvando(false)
    }
  }

  return (
    <>
      <Header titulo="Marcos e Conquistas" subtitulo="Histórico de avanços do Bernardo" />

      <div className="p-4 md:p-6 space-y-6">

        {/* Formulário de novo marco */}
        <div className="card p-5">
          <h2 className="section-title mb-4">⭐ Registrar nova conquista</h2>
          <form onSubmit={handleCriar} className="flex flex-col sm:flex-row gap-3">
            <input
              className="input flex-1"
              placeholder="Descreva a conquista (ex: Disse 'agua' espontaneamente)"
              value={descricao}
              onChange={e => setDescricao(e.target.value)}
            />
            <input
              type="date"
              className="input sm:w-44"
              value={dataMarco}
              onChange={e => setDataMarco(e.target.value)}
            />
            <button type="submit" disabled={salvando || !descricao} className="btn-primary whitespace-nowrap">
              {salvando ? 'Salvando...' : '+ Registrar'}
            </button>
          </form>
          {erro && <p className="text-sm text-manolo-danger mt-2">{erro}</p>}
        </div>

        {/* Timeline */}
        <div className="card p-5">
          <h2 className="section-title mb-5">Cronologia</h2>

          {loading && (
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex gap-4">
                  <div className="skeleton w-3 h-3 rounded-full mt-1.5 flex-shrink-0" />
                  <div className="flex-1 space-y-2">
                    <div className="skeleton h-4 w-3/4 rounded" />
                    <div className="skeleton h-3 w-1/3 rounded" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {!loading && marcos.length === 0 && (
            <p className="text-manolo-muted text-sm">
              Nenhum marco registrado ainda. Adicione a primeira conquista acima!
            </p>
          )}

          {!loading && (
            <div className="relative">
              {/* Linha vertical da timeline */}
              <div className="absolute left-1.5 top-0 bottom-0 w-px bg-neutral-border" />

              <div className="space-y-5 pl-8">
                {marcos.map((m, idx) => (
                  <div key={m.id} className="relative animate-fade-in" style={{ animationDelay: `${idx * 60}ms` }}>
                    {/* Ponto da timeline */}
                    <div className="absolute -left-8 top-1.5 w-3 h-3 rounded-full bg-accent border-2 border-neutral-surface shadow" />

                    <div className="card p-4 hover:shadow-card-hover transition-shadow">
                      <p className="text-sm font-medium text-manolo-text leading-snug">{m.descricao}</p>
                      <div className="flex items-center gap-3 mt-2">
                        <span className="text-xs text-manolo-muted">
                          {format(new Date(m.data_marco + 'T12:00:00'), "d 'de' MMMM 'de' yyyy", { locale: ptBR })}
                        </span>
                        {m.registrado_por && (
                          <span className="text-xs text-manolo-muted">· {m.registrado_por}</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

      </div>
    </>
  )
}
