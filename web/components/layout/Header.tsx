'use client'

import { useRef, useState, useEffect } from 'react'
import { getCriancas, uploadFotoCrianca } from '@/lib/api'
import { getCriancaSelecionada, setCriancaSelecionada } from '@/lib/auth'
import type { Crianca } from '@/types/manolo'

interface HeaderProps {
  titulo: string
  subtitulo?: string
}

export function Header({ titulo, subtitulo }: HeaderProps) {
  const [criancas, setCriancas] = useState<Crianca[]>([])
  const [criancaId, setCriancaId] = useState<string>('')
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

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

  const handleFotoClick = () => {
    fileInputRef.current?.click()
  }

  const handleFotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !criancaId) return

    try {
      setUploading(true)
      const res = await uploadFotoCrianca(criancaId, file)
      // Atualizar a URL na criança local
      setCriancas(prev => prev.map(c => c.id === criancaId ? { ...c, foto_url: res.foto_url } : c))
    } catch (err) {
      alert('Erro ao enviar foto.')
    } finally {
      setUploading(false)
    }
  }

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
            <input 
              type="file" 
              accept="image/*" 
              ref={fileInputRef}
              onChange={handleFotoUpload}
              className="hidden"
            />
            <div 
              className={`w-8 h-8 rounded-pill bg-accent flex items-center justify-center overflow-hidden cursor-pointer transition-opacity hover:opacity-80 relative ${uploading ? 'opacity-50' : ''}`}
              onClick={handleFotoClick}
              title="Mudar foto de perfil"
            >
              {criancaSelecionada?.foto_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={criancaSelecionada.foto_url} alt={criancaSelecionada.nome} className="w-full h-full object-cover" />
              ) : (
                <span className="text-white text-xs font-bold">
                  {criancaSelecionada?.nome?.[0] ?? 'B'}
                </span>
              )}
              {uploading && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/20">
                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                </div>
              )}
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
