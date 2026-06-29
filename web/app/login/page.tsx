'use client'

import { useState } from 'react'
import { actionLogin } from '@/app/actions'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [carregando, setCarregando] = useState(false)
  const router = useRouter()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !senha) return
    
    setCarregando(true)
    setErro(null)
    
    try {
      const res = await actionLogin(email, senha)
      if (res.sucesso) {
        // Redirecionamento e reload para carregar os contextos adequados
        router.push('/dashboard')
      } else {
        setErro(res.erro || 'Falha no login')
      }
    } catch (err: any) {
      setErro('Ocorreu um erro inesperado')
    } finally {
      setCarregando(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-bg p-4">
      <div className="card w-full max-w-md p-8 animate-fade-in">
        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto flex items-center justify-center mb-2">
            <img src="/logo.png" alt="Manolo" className="w-full h-full object-contain" />
          </div>
          <h1 className="text-2xl font-bold text-manolo-text">Manolo</h1>
          <p className="text-sm text-manolo-muted mt-1">Acesso ao Dashboard</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="label">Email</label>
            <input 
              type="email" 
              className="input" 
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="seu@email.com"
              required
            />
          </div>
          <div>
            <label className="label">Senha</label>
            <input 
              type="password" 
              className="input" 
              value={senha}
              onChange={e => setSenha(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>
          
          {erro && (
            <div className="p-3 bg-red-50 border border-red-100 rounded-lg text-sm text-red-600">
              {erro}
            </div>
          )}

          <button 
            type="submit" 
            className="btn-primary w-full py-3 mt-2"
            disabled={carregando || !email || !senha}
          >
            {carregando ? 'Entrando...' : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  )
}
