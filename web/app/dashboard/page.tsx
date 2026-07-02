'use client'

import { useEffect, useState } from 'react'
import { Header } from '@/components/layout/Header'
import { getPerfil, getMarcos } from '@/lib/api'
import { getCriancaSelecionada } from '@/lib/auth'
import type { PerfilVivo, Marco } from '@/types/manolo'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

// ============================================================
// CARD DE DOMÍNIO
// ============================================================

interface DomainCardProps {
  titulo: string
  emoji: string
  cor: string
  children: React.ReactNode
}

function DomainCard({ titulo, emoji, cor, children }: DomainCardProps) {
  return (
    <div className={`domain-card border-t-4 animate-fade-in ${cor}`}>
      <div className="flex items-center gap-2">
        <span className="text-xl">{emoji}</span>
        <h2 className="section-title">{titulo}</h2>
      </div>
      <div className="space-y-1.5 text-sm text-manolo-text">{children}</div>
    </div>
  )
}

function Campo({ label, valor }: { label: string; valor?: string | boolean | null | string[] | number }) {
  if (valor === null || valor === undefined || valor === '') return null

  let display: string
  if (typeof valor === 'boolean') display = valor ? 'Sim' : 'Não'
  else if (Array.isArray(valor)) display = valor.join(', ')
  else display = String(valor)

  return (
    <div className="flex gap-2">
      <span className="text-manolo-muted flex-shrink-0 w-32 text-xs pt-0.5">{label}</span>
      <span className="text-manolo-text text-sm">{display}</span>
    </div>
  )
}

// ============================================================
// BADGE DE ATUALIZAÇÃO
// ============================================================
function AtualizadoEm({ data }: { data: string }) {
  const formatted = format(new Date(data), "d 'de' MMMM 'de' yyyy, HH:mm", { locale: ptBR })
  return (
    <span className="badge badge-green text-xs">
      Atualizado em {formatted}
    </span>
  )
}

function formatKey(key: string): string {
  const spaced = key.replace(/_/g, ' ')
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

// ============================================================
// SKELETON
// ============================================================
function SkeletonDashboard() {
  return (
    <div className="p-6 space-y-6">
      <div className="skeleton h-6 w-48 rounded" />
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="card p-5 space-y-3">
            <div className="skeleton h-5 w-32 rounded" />
            <div className="skeleton h-4 w-full rounded" />
            <div className="skeleton h-4 w-3/4 rounded" />
            <div className="skeleton h-4 w-1/2 rounded" />
          </div>
        ))}
      </div>
    </div>
  )
}

// ============================================================
// PÁGINA
// ============================================================

export default function DashboardPage() {
  const [perfil, setPerfil] = useState<PerfilVivo | null>(null)
  const [marcos, setMarcos] = useState<Marco[]>([])
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    const criancaId = getCriancaSelecionada()
    Promise.all([getPerfil(criancaId), getMarcos(criancaId)])
      .then(([p, m]) => {
        setPerfil(p)
        setMarcos(m.slice(0, 5))
      })
      .catch(e => setErro(e.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <>
      <Header titulo="Dashboard" subtitulo="Perfil vivo e últimas conquistas" />

      {loading && <SkeletonDashboard />}

      {erro && (
        <div className="p-6">
          <div className="card p-5 border-l-4 border-manolo-danger text-manolo-danger text-sm">
            {erro}
          </div>
        </div>
      )}

      {perfil && !loading && (
        <div className="p-4 md:p-6 space-y-6 animate-fade-in">

          {/* Cabeçalho do perfil */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <h2 className="text-2xl font-bold text-manolo-text">{perfil.nome_crianca}</h2>
              <p className="text-manolo-muted text-sm">
                Nascido em {format(new Date(perfil.data_nascimento + 'T12:00:00'), "d 'de' MMMM 'de' yyyy", { locale: ptBR })}
              </p>
            </div>
            <AtualizadoEm data={perfil.atualizado_em} />
          </div>

          {/* Resumo geral */}
          {perfil.resumo_geral && (
            <div className="card p-5 border-l-4 border-primary">
              <p className="text-sm text-manolo-text leading-relaxed">{perfil.resumo_geral}</p>
            </div>
          )}

          {/* Cards por domínio */}
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">

            <DomainCard titulo="Comunicação" emoji="💬" cor="border-primary">
              {perfil.comunicacao && Object.entries(perfil.comunicacao).map(([k, v]) => (
                <Campo key={k} label={formatKey(k)} valor={v as any} />
              ))}
            </DomainCard>

            <DomainCard titulo="Motor" emoji="🤸" cor="border-accent">
              {perfil.motor && Object.entries(perfil.motor).map(([k, v]) => (
                <Campo key={k} label={formatKey(k)} valor={v as any} />
              ))}
            </DomainCard>

            <DomainCard titulo="Alimentação" emoji="🍽️" cor="border-amber-400">
              {perfil.alimentacao && Object.entries(perfil.alimentacao).map(([k, v]) => (
                <Campo key={k} label={formatKey(k)} valor={v as any} />
              ))}
            </DomainCard>

            <DomainCard titulo="Sono" emoji="🌙" cor="border-indigo-400">
              {perfil.sono && Object.entries(perfil.sono).map(([k, v]) => (
                <Campo key={k} label={formatKey(k)} valor={v as any} />
              ))}
            </DomainCard>

            <DomainCard titulo="Regulação" emoji="🧘" cor="border-rose-400">
              {perfil.regulacao && Object.entries(perfil.regulacao).map(([k, v]) => (
                <Campo key={k} label={formatKey(k)} valor={v as any} />
              ))}
            </DomainCard>
          </div>

          {/* Últimas conquistas */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="section-title">⭐ Últimas conquistas</h2>
              <a href="/dashboard/marcos" className="text-xs text-primary hover:underline">Ver todas</a>
            </div>

            {marcos.length === 0 ? (
              <p className="text-sm text-manolo-muted">Nenhum marco registrado ainda.</p>
            ) : (
              <div className="space-y-3">
                {marcos.map(m => (
                  <div key={m.id} className="flex items-start gap-3 py-2 border-b border-neutral-border last:border-0">
                    <div className="w-2 h-2 rounded-full bg-accent mt-2 flex-shrink-0" />
                    <div>
                      <p className="text-sm text-manolo-text">{m.descricao}</p>
                      <p className="text-xs text-manolo-muted mt-0.5">
                        {format(new Date(m.data_marco + 'T12:00:00'), "d 'de' MMMM 'de' yyyy", { locale: ptBR })}
                        {m.registrado_por && ` · ${m.registrado_por}`}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      )}
    </>
  )
}
