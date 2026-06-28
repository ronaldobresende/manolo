'use client'

import { useEffect, useState } from 'react'

export function useAuth() {
  const [usuarioId, setUsuarioId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Tenta ler o usuario_id dos cookies
    const match = document.cookie.match(/(^| )manolo_user_id=([^;]+)/)
    if (match) {
      setUsuarioId(match[2])
    }
    setIsLoading(false)
  }, [])

  return {
    usuarioId,
    isLoading,
    isAuthenticated: !!usuarioId
  }
}
