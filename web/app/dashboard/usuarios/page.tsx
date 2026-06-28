'use client'

import { useEffect, useState } from 'react'
import { Header } from '@/components/layout/Header'
import { getUsuarios, criarUsuario, toggleUsuarioAtivo } from '@/lib/api'
import type { Usuario } from '@/types/manolo'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

const PERFIS = ['admin', 'família', 'terapeuta'] as const

export default function UsuariosPage() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [loading, setLoading] = useState(true)
  const [formOpen, setFormOpen] = useState(false)
  const [nome, setNome] = useState('')
  const [telefone, setTelefone] = useState('')
  const [email, setEmail] = useState('')
  const [perfil, setPerfil] = useState<typeof PERFIS[number]>('família')
  const [especialidade, setEspecialidade] = useState('')
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    getUsuarios()
      .then(setUsuarios)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleCriar = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!nome || !telefone) { setErro('Nome e telefone são obrigatórios.'); return }
    setSalvando(true); setErro(null)
    try {
      const novo = await criarUsuario({ nome, telefone_whatsapp: telefone, email, perfil, especialidade: especialidade || undefined })
      setUsuarios(prev => [novo, ...prev])
      setFormOpen(false)
      setNome(''); setTelefone(''); setEmail(''); setEspecialidade('')
    } catch (e: unknown) {
      setErro(e instanceof Error ? e.message : 'Erro ao cadastrar.')
    } finally {
      setSalvando(false)
    }
  }

  const handleToggle = async (id: string) => {
    try {
      const atualizado = await toggleUsuarioAtivo(id)
      setUsuarios(prev => prev.map(u => u.id === id ? { ...u, ativo: atualizado.ativo } : u))
    } catch {}
  }

  const PERFIL_CLASSE: Record<string, string> = {
    admin:      'badge-red',
    família:    'badge-green',
    terapeuta:  'badge-yellow',
  }

  return (
    <>
      <Header titulo="Usuários" subtitulo="Gestão de acesso ao sistema" />

      <div className="p-4 md:p-6 space-y-5">

        {/* Botão de cadastro */}
        <div className="flex justify-end">
          <button className="btn-primary" onClick={() => setFormOpen(!formOpen)}>
            {formOpen ? 'Cancelar' : '+ Adicionar usuário'}
          </button>
        </div>

        {/* Formulário */}
        {formOpen && (
          <div className="card p-5 animate-slide-up">
            <h3 className="section-title mb-4">Novo usuário</h3>
            <form onSubmit={handleCriar} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="label">Nome *</label>
                <input className="input" value={nome} onChange={e => setNome(e.target.value)} placeholder="Nome completo" />
              </div>
              <div>
                <label className="label">Telefone WhatsApp *</label>
                <input className="input" value={telefone} onChange={e => setTelefone(e.target.value)} placeholder="5511999999999" />
              </div>
              <div>
                <label className="label">Email</label>
                <input type="email" className="input" value={email} onChange={e => setEmail(e.target.value)} placeholder="email@exemplo.com" />
              </div>
              <div>
                <label className="label">Perfil *</label>
                <select className="select" value={perfil} onChange={e => setPerfil(e.target.value as typeof PERFIS[number])}>
                  {PERFIS.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              {perfil === 'terapeuta' && (
                <div className="sm:col-span-2">
                  <label className="label">Especialidade</label>
                  <input className="input" value={especialidade} onChange={e => setEspecialidade(e.target.value)} placeholder="Fono, TO, Psicólogo..." />
                </div>
              )}
              {erro && <p className="sm:col-span-2 text-sm text-manolo-danger">{erro}</p>}
              <div className="sm:col-span-2">
                <button type="submit" disabled={salvando} className="btn-primary">
                  {salvando ? 'Cadastrando...' : 'Cadastrar usuário'}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Tabela */}
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-primary-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary uppercase tracking-wide">Nome</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary uppercase tracking-wide hidden sm:table-cell">Telefone</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary uppercase tracking-wide">Perfil</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary uppercase tracking-wide hidden md:table-cell">Cadastrado</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary uppercase tracking-wide">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary uppercase tracking-wide">Ação</th>
              </tr>
            </thead>
            <tbody>
              {loading && [...Array(4)].map((_, i) => (
                <tr key={i} className="border-b border-neutral-border">
                  {[...Array(6)].map((_, j) => (
                    <td key={j} className="px-4 py-3"><div className="skeleton h-4 rounded" /></td>
                  ))}
                </tr>
              ))}

              {!loading && usuarios.map(u => (
                <tr key={u.id} className="border-b border-neutral-border last:border-0">
                  <td className="px-4 py-3 font-medium text-manolo-text">{u.nome}</td>
                  <td className="px-4 py-3 text-manolo-muted hidden sm:table-cell font-mono text-xs">{u.telefone_whatsapp}</td>
                  <td className="px-4 py-3">
                    <span className={`badge ${PERFIL_CLASSE[u.perfil] || 'badge-gray'}`}>{u.perfil}</span>
                  </td>
                  <td className="px-4 py-3 text-manolo-muted text-xs hidden md:table-cell">
                    {format(new Date(u.criado_em), "d/MM/yyyy")}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`badge ${u.ativo ? 'badge-green' : 'badge-gray'}`}>
                      {u.ativo ? '● Ativo' : '○ Inativo'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleToggle(u.id)}
                      className="btn-ghost text-xs py-1"
                    >
                      {u.ativo ? 'Desativar' : 'Ativar'}
                    </button>
                  </td>
                </tr>
              ))}

              {!loading && usuarios.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-manolo-muted">Nenhum usuário encontrado.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

      </div>
    </>
  )
}
