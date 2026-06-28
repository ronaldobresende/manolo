'use server'

import { cookies } from 'next/headers'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function actionLogin(email: string, senha: string) {
  try {
    const params = new URLSearchParams()
    params.append('username', email)
    params.append('password', senha)

    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: params.toString(),
      cache: 'no-store'
    })

    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      return { sucesso: false, erro: data.detail || 'Falha ao autenticar' }
    }

    const data = await res.json()
    
    // Salvar o cookie. Importante: secure em prod, mas não httpOnly para podermos 
    // ler no client side e enviar no apiFetch (arquitetura MVP da Fase 4.1).
    cookies().set('manolo_token', data.access_token, {
      path: '/',
      maxAge: 8 * 60 * 60, // 8 horas
      httpOnly: false, // Permitir leitura pelo client side
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
    })
    
    // Opcionalmente salvar informações básicas no cookie para acesso rápido
    if (data.user_id) {
      cookies().set('manolo_user_id', data.user_id, {
        path: '/', maxAge: 8 * 60 * 60, httpOnly: false
      })
    }
    
    return { sucesso: true }
  } catch (error: any) {
    return { sucesso: false, erro: 'Erro de conexão com o servidor' }
  }
}

export async function actionLogout() {
  cookies().delete('manolo_token')
  cookies().delete('manolo_user_id')
  return { sucesso: true }
}
