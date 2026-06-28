import { redirect } from 'next/navigation'

/**
 * Rota raiz — redireciona para /dashboard.
 * Fase 4.1: verificar JWT antes do redirect.
 */
export default function Home() {
  redirect('/dashboard')
}
