/**
 * API client do Manolo Web App.
 * Todas as chamadas ao backend FastAPI passam por aqui.
 * Sem autenticação no MVP (Fase 4) — débito técnico para Fase 4.1.
 */

import type {
  PerfilVivo,
  ChecklistsResponse,
  ChecklistDetalhado,
  Documento,
  Marco,
  Atividade,
  Crianca,
  Usuario,
} from '@/types/manolo'

// ============================================================
// CONFIGURAÇÃO BASE
// ============================================================

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/** Erro customizado com status HTTP */
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`

  // Lê o token do cookie (funciona apenas no client-side, se httpOnly for false)
  let token = ''
  if (typeof document !== 'undefined') {
    const match = document.cookie.match(/(^| )manolo_token=([^;]+)/)
    if (match) token = match[2]
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...options?.headers as Record<string, string>,
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(url, {
    headers,
    ...options,
  })

  if (res.status === 401 && typeof window !== 'undefined') {
    // Redireciona para o login em caso de token inválido ou expirado
    window.location.href = '/login'
    throw new ApiError(401, 'Sessão expirada')
  }

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, detail.detail || `Erro ${res.status}`)
  }

  // Respostas 204 (No Content) não têm body
  if (res.status === 204) return undefined as T

  return res.json()
}

// ============================================================
// CRIANÇAS
// ============================================================

export async function getCriancas(): Promise<Crianca[]> {
  return apiFetch('/api/criancas')
}

export async function uploadFotoCrianca(criancaId: string, file: File): Promise<{ foto_url: string }> {
  // Para upload de arquivo, não usamos json e não definimos Content-Type
  // pois o fetch cuidará de montar o boundary do FormData automaticamente
  const formData = new FormData()
  formData.append('file', file)

  let token = ''
  if (typeof document !== 'undefined') {
    const match = document.cookie.match(/(^| )manolo_token=([^;]+)/)
    if (match) token = match[2]
  }

  const res = await fetch(`${API_BASE}/api/criancas/${criancaId}/foto`, {
    method: 'POST',
    body: formData,
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })

  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new ApiError(res.status, data.detail || 'Erro ao enviar foto')
  }

  return res.json()
}

// ============================================================
// PERFIL VIVO
// ============================================================

export async function getPerfil(criancaId: string): Promise<PerfilVivo> {
  return apiFetch(`/api/perfil/${criancaId}`)
}

// ============================================================
// CHECKLISTS
// ============================================================

export interface ChecklistFiltros {
  inicio?: string
  fim?: string
  pagina?: number
  por_pagina?: number
}

export async function getChecklists(
  criancaId: string,
  filtros?: ChecklistFiltros
): Promise<ChecklistsResponse> {
  const params = new URLSearchParams()
  if (filtros?.inicio)    params.set('inicio', filtros.inicio)
  if (filtros?.fim)       params.set('fim', filtros.fim)
  if (filtros?.pagina)    params.set('pagina', String(filtros.pagina))
  if (filtros?.por_pagina) params.set('por_pagina', String(filtros.por_pagina))
  const qs = params.toString() ? `?${params.toString()}` : ''
  return apiFetch(`/api/checklists/${criancaId}${qs}`)
}

export async function getChecklistDetalhado(
  criancaId: string,
  data: string
): Promise<ChecklistDetalhado> {
  return apiFetch(`/api/checklists/${criancaId}/${data}`)
}

// ============================================================
// DOCUMENTOS
// ============================================================

export async function getDocumentos(criancaId: string): Promise<Documento[]> {
  return apiFetch(`/api/documentos/${criancaId}`)
}

export async function uploadDocumento(
  criancaId: string,
  file: File,
  meta: { tipo: string; especialidade?: string; titulo: string; data_documento?: string }
): Promise<Documento> {
  const form = new FormData()
  form.append('arquivo', file)
  form.append('tipo', meta.tipo)
  form.append('especialidade', meta.especialidade || '')
  form.append('titulo', meta.titulo)
  form.append('data_documento', meta.data_documento || '')

  const res = await fetch(`${API_BASE}/api/documentos/${criancaId}`, {
    method: 'POST',
    body: form,
    // Não setamos Content-Type aqui — o browser define o boundary do multipart
  })

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, detail.detail || `Erro ${res.status}`)
  }

  return res.json()
}

// ============================================================
// MARCOS
// ============================================================

export async function getMarcos(criancaId: string): Promise<Marco[]> {
  return apiFetch(`/api/marcos/${criancaId}`)
}

export async function criarMarco(
  criancaId: string,
  data: { descricao: string; data_marco: string }
): Promise<Marco> {
  return apiFetch(`/api/marcos/${criancaId}`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ============================================================
// ATIVIDADES
// ============================================================

export async function getAtividades(criancaId: string): Promise<Atividade[]> {
  return apiFetch(`/api/atividades/${criancaId}`)
}

export async function criarAtividade(data: {
  titulo: string
  descricao: string
  tipo: string
  objetivo?: string
  materiais?: string[]
  duracao_minutos?: number
  crianca_id: string
}): Promise<Atividade> {
  return apiFetch('/api/atividades', { method: 'POST', body: JSON.stringify(data) })
}

export async function atualizarStatusAtividade(
  atividadeId: string,
  data: { status: string; feedback?: string; crianca_id: string }
): Promise<{ ok: boolean; status: string }> {
  return apiFetch(`/api/atividades/${atividadeId}/status`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

// ============================================================
// CHAT
// ============================================================

export async function enviarMensagemChat(data: {
  mensagem: string
  crianca_id: string
  session_id?: string
}): Promise<{ resposta: string; session_id: string }> {
  return apiFetch('/api/chat', { method: 'POST', body: JSON.stringify(data) })
}

// ============================================================
// USUÁRIOS
// ============================================================

export async function getUsuarios(): Promise<Usuario[]> {
  return apiFetch('/api/usuarios')
}

export async function criarUsuario(data: {
  nome: string
  telefone_whatsapp: string
  email?: string
  perfil: string
  especialidade?: string
}): Promise<Usuario> {
  return apiFetch('/api/usuarios', { method: 'POST', body: JSON.stringify(data) })
}

export async function toggleUsuarioAtivo(
  usuarioId: string
): Promise<{ id: string; nome: string; ativo: boolean }> {
  return apiFetch(`/api/usuarios/${usuarioId}/ativo`, { method: 'PATCH' })
}

export async function atualizarUsuario(
  usuarioId: string,
  data: {
    nome?: string
    telefone_whatsapp?: string
    email?: string
    perfil?: string
    senha?: string
  }
): Promise<Usuario> {
  return apiFetch(`/api/usuarios/${usuarioId}`, { method: 'PATCH', body: JSON.stringify(data) })
}
