'use client'

import { useState, useRef, useEffect } from 'react'
import { Header } from '@/components/layout/Header'
import { enviarMensagemChat } from '@/lib/api'
import { getCriancaSelecionada } from '@/lib/auth'
import type { ChatMessage } from '@/types/manolo'
import { format } from 'date-fns'
import clsx from 'clsx'

const SUGESTOES = [
  'Como foi a comunicação essa semana?',
  'Prepara um resumo para a sessão de fono',
  'Compare o sono de maio com junho',
  'Quais palavras novas surgiram recentemente?',
  'Quais são os principais gatilhos de crise?',
  'Sugira uma atividade para estimular o apontar',
]

export default function ChatPage() {
  const [mensagens, setMensagens] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [carregando, setCarregando] = useState(false)
  const [sessionId] = useState(`web-${Date.now()}`)
  const [criancaId] = useState(getCriancaSelecionada)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Scroll automático para o final
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [mensagens])

  const enviar = async (texto?: string) => {
    const msg = texto || input.trim()
    if (!msg || carregando) return

    const userMsg: ChatMessage = {
      role: 'user',
      content: msg,
      timestamp: new Date().toISOString(),
    }

    setMensagens(prev => [...prev, userMsg])
    setInput('')
    setCarregando(true)

    try {
      const { resposta } = await enviarMensagemChat({
        mensagem: msg,
        crianca_id: criancaId,
        session_id: sessionId,
      })

      const asstMsg: ChatMessage = {
        role: 'assistant',
        content: resposta,
        timestamp: new Date().toISOString(),
      }
      setMensagens(prev => [...prev, asstMsg])
    } catch (e: unknown) {
      const errMsg: ChatMessage = {
        role: 'assistant',
        content: '⚠️ Não consegui processar sua mensagem. Tente novamente.',
        timestamp: new Date().toISOString(),
      }
      setMensagens(prev => [...prev, errMsg])
    } finally {
      setCarregando(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      enviar()
    }
  }

  return (
    <>
      <Header titulo="Chat" subtitulo="Converse com o agente Manolo" />

      <div className="flex flex-col flex-1 min-h-0">

        {/* Área de mensagens */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">

          {/* Estado vazio com sugestões */}
          {mensagens.length === 0 && (
            <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
              <div className="text-center py-8">
                <div className="w-16 h-16 rounded-full bg-primary flex items-center justify-center mx-auto mb-4">
                  <span className="text-white text-2xl font-bold">M</span>
                </div>
                <h2 className="text-xl font-semibold text-manolo-text">Olá! Sou o Manolo.</h2>
                <p className="text-manolo-muted mt-2 text-sm leading-relaxed">
                  Posso responder perguntas sobre o desenvolvimento do Bernardo,<br />
                  analisar padrões nos checklists ou preparar resumos para as sessões.
                </p>
              </div>

              <div>
                <p className="text-xs font-medium text-manolo-muted uppercase tracking-wide mb-3">Sugestões de pergunta</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {SUGESTOES.map(s => (
                    <button
                      key={s}
                      onClick={() => enviar(s)}
                      className="text-left p-3 card text-sm text-manolo-text hover:border-primary hover:text-primary transition-colors"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Mensagens */}
          {mensagens.map((m, idx) => (
            <div
              key={idx}
              className={clsx(
                'flex gap-3 max-w-3xl animate-fade-in',
                m.role === 'user' ? 'ml-auto flex-row-reverse' : ''
              )}
            >
              {/* Avatar */}
              <div className={clsx(
                'w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-1 overflow-hidden',
                m.role === 'user'
                  ? 'bg-neutral-border text-manolo-muted'
                  : 'bg-transparent'
              )}>
                {m.role === 'user' ? 'Eu' : <img src="/logo.png" alt="Manolo" className="w-full h-full object-cover" />}
              </div>

              {/* Balão */}
              <div className={clsx(
                'px-4 py-3 rounded-2xl text-sm leading-relaxed max-w-[80%]',
                m.role === 'user'
                  ? 'bg-primary text-white rounded-tr-sm'
                  : 'bg-neutral-surface border border-neutral-border text-manolo-text rounded-tl-sm shadow-card'
              )}>
                {/* Preservar quebras de linha */}
                {m.content.split('\n').map((linha, i) => (
                  <span key={i}>
                    {linha}
                    {i < m.content.split('\n').length - 1 && <br />}
                  </span>
                ))}
                <span className={clsx(
                  'block text-xs mt-1',
                  m.role === 'user' ? 'text-primary-200' : 'text-manolo-muted'
                )}>
                  {format(new Date(m.timestamp), 'HH:mm')}
                </span>
              </div>
            </div>
          ))}

          {/* Indicador de digitando */}
          {carregando && (
            <div className="flex gap-3 max-w-3xl animate-fade-in">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-xs font-bold text-white flex-shrink-0 mt-1">M</div>
              <div className="bg-neutral-surface border border-neutral-border rounded-2xl rounded-tl-sm px-4 py-3 shadow-card">
                <div className="flex gap-1 items-center h-4">
                  {[0, 1, 2].map(i => (
                    <div
                      key={i}
                      className="w-2 h-2 rounded-full bg-manolo-muted animate-bounce"
                      style={{ animationDelay: `${i * 150}ms` }}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="border-t border-neutral-border p-4 bg-neutral-surface">
          <div className="max-w-3xl mx-auto flex gap-3 items-end">
            <textarea
              ref={inputRef}
              className="input flex-1 resize-none"
              rows={1}
              placeholder="Escreva sua pergunta... (Enter para enviar, Shift+Enter para nova linha)"
              value={input}
              onChange={e => {
                setInput(e.target.value)
                // Auto-resize
                e.target.style.height = 'auto'
                e.target.style.height = `${Math.min(e.target.scrollHeight, 140)}px`
              }}
              onKeyDown={handleKeyDown}
              disabled={carregando}
            />
            <button
              onClick={() => enviar()}
              disabled={!input.trim() || carregando}
              className="btn-primary h-10 px-5 flex-shrink-0"
            >
              Enviar
            </button>
          </div>
        </div>

      </div>
    </>
  )
}
