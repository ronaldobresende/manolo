/**
 * Auth helpers — STUB para Fase 4.1.
 * Autenticação desabilitada no MVP (Fase 4).
 * Quando implementada: JWT armazenado em cookie httpOnly.
 *
 * DÉBITO TÉCNICO — ver DEBITOS_TECNICOS.md
 */

/** Criança selecionada atualmente — default = Bernardo (piloto) */
export const CRIANCA_ID_PILOTO = process.env.NEXT_PUBLIC_CRIANCA_ID_PILOTO
  || 'c0000000-0000-0000-0000-000000000001'

/** Usuário piloto (admin) usado enquanto não há autenticação */
export const USUARIO_ID_PILOTO = process.env.NEXT_PUBLIC_USUARIO_ID_PILOTO
  || 'b0000000-0000-0000-0000-000000000001'

/**
 * Retorna a criança selecionada (localStorage no cliente).
 * Fase 4: fixado no Bernardo se não houver outra seleção.
 */
export function getCriancaSelecionada(): string {
  if (typeof window === 'undefined') return CRIANCA_ID_PILOTO
  return localStorage.getItem('manolo_crianca_id') || CRIANCA_ID_PILOTO
}

export function setCriancaSelecionada(criancaId: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem('manolo_crianca_id', criancaId)
  }
}

// ============================================================
// TODO Fase 4.1 — Implementar:
// - POST /api/auth/login → JWT
// - Armazenar token em cookie httpOnly via Server Action
// - Middleware Next.js: verificar cookie em /dashboard/*
// - Renovação automática 30min antes de expirar (8h total)
// - Logout: invalidar cookie server-side
// ============================================================
