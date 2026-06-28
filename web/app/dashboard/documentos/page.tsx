'use client'

import { useEffect, useState, useRef } from 'react'
import { Header } from '@/components/layout/Header'
import { getDocumentos, uploadDocumento } from '@/lib/api'
import { getCriancaSelecionada } from '@/lib/auth'
import type { Documento, TipoDocumento } from '@/types/manolo'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

const TIPOS: { value: TipoDocumento; label: string }[] = [
  { value: 'laudo',            label: 'Laudo' },
  { value: 'relatorio_sessao', label: 'Relatório de Sessão' },
  { value: 'avaliacao',        label: 'Avaliação' },
  { value: 'receita',          label: 'Receita' },
  { value: 'outro',            label: 'Outro' },
]

// ============================================================
// FORMULÁRIO DE UPLOAD
// ============================================================

interface FormUploadProps {
  criancaId: string
  onUploadSucesso: (doc: Documento) => void
}

function FormUpload({ criancaId, onUploadSucesso }: FormUploadProps) {
  const [open, setOpen] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [tipo, setTipo] = useState<TipoDocumento>('laudo')
  const [especialidade, setEspecialidade] = useState('')
  const [titulo, setTitulo] = useState('')
  const [dataDoc, setDataDoc] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const dropRef = useRef<HTMLDivElement>(null)

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const f = e.dataTransfer.files[0]
    if (f?.type === 'application/pdf') setFile(f)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || !titulo) { setErro('Arquivo e título são obrigatórios.'); return }
    setEnviando(true); setErro(null)
    try {
      const doc = await uploadDocumento(criancaId, file, { tipo, especialidade, titulo, data_documento: dataDoc })
      onUploadSucesso(doc)
      setOpen(false)
      setFile(null); setTitulo(''); setEspecialidade(''); setDataDoc('')
    } catch (e: unknown) {
      setErro(e instanceof Error ? e.message : 'Erro ao enviar.')
    } finally {
      setEnviando(false)
    }
  }

  if (!open) {
    return (
      <button className="btn-primary" onClick={() => setOpen(true)}>
        + Enviar PDF
      </button>
    )
  }

  return (
    <div className="card p-5 animate-slide-up">
      <div className="flex items-center justify-between mb-4">
        <h3 className="section-title">Enviar novo documento</h3>
        <button className="btn-ghost text-xs" onClick={() => setOpen(false)}>Cancelar</button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Drag & drop */}
        <div
          ref={dropRef}
          onDragOver={e => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => document.getElementById('pdf-input')?.click()}
          className="border-2 border-dashed border-neutral-border rounded-card p-8 text-center cursor-pointer hover:border-primary hover:bg-primary-50 transition-colors"
        >
          <input
            id="pdf-input"
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={e => setFile(e.target.files?.[0] || null)}
          />
          {file ? (
            <div>
              <p className="text-sm font-medium text-primary">📄 {file.name}</p>
              <p className="text-xs text-manolo-muted mt-1">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
            </div>
          ) : (
            <div>
              <p className="text-2xl mb-2">📁</p>
              <p className="text-sm text-manolo-muted">Arraste o PDF aqui ou clique para selecionar</p>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="label">Tipo *</label>
            <select className="select" value={tipo} onChange={e => setTipo(e.target.value as TipoDocumento)}>
              {TIPOS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Especialidade</label>
            <input className="input" value={especialidade} onChange={e => setEspecialidade(e.target.value)} placeholder="Fono, TO, Neuropediatra..." />
          </div>
          <div className="sm:col-span-2">
            <label className="label">Título *</label>
            <input className="input" value={titulo} onChange={e => setTitulo(e.target.value)} placeholder="Ex: Laudo de avaliação fonoaudiológica" />
          </div>
          <div>
            <label className="label">Data do documento</label>
            <input type="date" className="input" value={dataDoc} onChange={e => setDataDoc(e.target.value)} />
          </div>
        </div>

        {erro && <p className="text-sm text-manolo-danger">{erro}</p>}

        <div className="flex gap-3">
          <button type="submit" disabled={enviando} className="btn-primary">
            {enviando ? 'Enviando e indexando...' : 'Enviar documento'}
          </button>
          {enviando && (
            <p className="text-xs text-manolo-muted self-center">
              Aguarde — o pipeline de ingestão pode levar até 1 minuto.
            </p>
          )}
        </div>
      </form>
    </div>
  )
}

// ============================================================
// PÁGINA
// ============================================================

export default function DocumentosPage() {
  const [docs, setDocs] = useState<Documento[]>([])
  const [loading, setLoading] = useState(true)
  const [criancaId] = useState(getCriancaSelecionada)

  useEffect(() => {
    getDocumentos(criancaId)
      .then(setDocs)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [criancaId])

  const handleUpload = (doc: Documento) => {
    setDocs(prev => [doc, ...prev])
  }

  return (
    <>
      <Header titulo="Documentos" subtitulo="Laudos, relatórios e avaliações indexados" />

      <div className="p-4 md:p-6 space-y-5">
        <div className="flex justify-end">
          <FormUpload criancaId={criancaId} onUploadSucesso={handleUpload} />
        </div>

        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-primary-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary uppercase tracking-wide">Título</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary uppercase tracking-wide hidden sm:table-cell">Tipo</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary uppercase tracking-wide hidden md:table-cell">Especialidade</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary uppercase tracking-wide hidden md:table-cell">Data</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary uppercase tracking-wide">Status</th>
              </tr>
            </thead>
            <tbody>
              {loading && [...Array(5)].map((_, i) => (
                <tr key={i} className="border-b border-neutral-border">
                  {[...Array(5)].map((_, j) => (
                    <td key={j} className="px-4 py-3"><div className="skeleton h-4 rounded" /></td>
                  ))}
                </tr>
              ))}

              {!loading && docs.map(doc => (
                <tr key={doc.id} className="border-b border-neutral-border last:border-0">
                  <td className="px-4 py-3 font-medium text-manolo-text">{doc.titulo}</td>
                  <td className="px-4 py-3 hidden sm:table-cell">
                    <span className="badge badge-gray capitalize">{doc.tipo?.replace('_', ' ')}</span>
                  </td>
                  <td className="px-4 py-3 text-manolo-muted hidden md:table-cell">
                    {doc.especialidade || '—'}
                  </td>
                  <td className="px-4 py-3 text-manolo-muted hidden md:table-cell">
                    {doc.data_documento
                      ? format(new Date(doc.data_documento + 'T12:00:00'), "d/MM/yyyy")
                      : '—'}
                  </td>
                  <td className="px-4 py-3">
                    {doc.processado
                      ? <span className="badge badge-green">✅ Indexado</span>
                      : <span className="badge badge-yellow animate-pulse-soft">⏳ Processando</span>
                    }
                  </td>
                </tr>
              ))}

              {!loading && docs.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-manolo-muted">
                    Nenhum documento indexado ainda.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
