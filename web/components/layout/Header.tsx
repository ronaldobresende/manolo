'use client'

import { useState, useEffect } from 'react'
import { getCriancas } from '@/lib/api'
import { getCriancaSelecionada, setCriancaSelecionada } from '@/lib/auth'
import type { Crianca } from '@/types/manolo'

interface HeaderProps {
  titulo: string
  subtitulo?: string
}

export function Header({ titulo, subtitulo }: HeaderProps) {
  const [criancas, setCriancas] = useState<Crianca[]>([])
  const [criancaId, setCriancaId] = useState<string>('')

  useEffect(() => {
    setCriancaId(getCriancaSelecionada())
    getCriancas()
      .then(setCriancas)
      .catch(() => {})
  }, [])

  const handleChangeCrianca = (id: string) => {
    setCriancaId(id)
    setCriancaSelecionada(id)
    // Recarregar a página para refletir a criança selecionada
    window.location.reload()
  }

  const criancaSelecionada = criancas.find(c => c.id === criancaId)

  return (
    <header className="sticky top-0 z-30 bg-neutral-surface/80 backdrop-blur-sm border-b border-neutral-border px-6 py-4 flex items-center justify-between gap-4">
      <div className="ml-10 md:ml-0">
        <h1 className="text-lg font-semibold text-manolo-text leading-tight">{titulo}</h1>
        {subtitulo && <p className="text-sm text-manolo-muted leading-tight">{subtitulo}</p>}
      </div>

      {/* Seletor de criança */}
      <div className="flex items-center gap-3">
        {criancas.length > 1 ? (
          <select
            className="select text-sm py-1.5 pr-8 w-auto"
            value={criancaId}
            onChange={e => handleChangeCrianca(e.target.value)}
          >
            {criancas.map(c => (
              <option key={c.id} value={c.id}>{c.nome}</option>
            ))}
          </select>
        ) : (
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-pill bg-accent flex items-center justify-center">
              <span className="text-white text-xs font-bold">
                {criancaSelecionada?.nome?.[0] ?? 'B'}
              </span>
            </div>
            <span className="text-sm font-medium text-manolo-text hidden sm:block">
              {criancaSelecionada?.nome ?? 'Bernardo'}
            </span>
          </div>
        )}
      </div>
    </header>
  )
}
