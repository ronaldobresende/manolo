'use client'

import { useEffect, useState } from 'react'
import { Header } from '@/components/layout/Header'
import { getChecklists, getChecklistDetalhado } from '@/lib/api'
import { getCriancaSelecionada } from '@/lib/auth'
import type { ChecklistResumo, ChecklistDetalhado, ResumoDia } from '@/types/manolo'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

// ============================================================
// HELPERS
// ============================================================

const RESUMO_LABEL: Record<ResumoDia, string> = {
  muito_bom: '🌟 Muito bom',
  bom:       '😊 Bom',
  regular:   '😐 Regular',
  'difícil': '😔 Difícil',
}

const RESUMO_CLASS: Record<ResumoDia, string> = {
  muito_bom: 'badge-green',
  bom:       'badge-green',
  regular:   'badge-yellow',
  'difícil': 'badge-red',
}

function formatData(iso: string) {
  return format(new Date(iso + 'T12:00:00'), "EEEE, d 'de' MMMM 'de' yyyy", { locale: ptBR })
}

// ============================================================
// MODAL DETALHE DO CHECKLIST
// ============================================================

function ModalChecklist({ data, criancaId, onClose }: {
  data: string
  criancaId: string
  onClose: () => void
}) {
  const [detalhe, setDetalhe] = useState<ChecklistDetalhado | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getChecklistDetalhado(criancaId, data)
      .then(setDetalhe)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [criancaId, data])

  function CampoSec({ label, val }: { label: string; val?: boolean | string | string[] | null | number }) {
    if (val === null || val === undefined || val === '') return null
    let display: string
    if (typeof val === 'boolean') display = val ? 'Sim' : 'Não'
    else if (Array.isArray(val)) display = val.join(', ')
    else display = String(val)
    return (
      <div className="flex gap-2 text-sm">
        <span className="text-manolo-muted w-40 flex-shrink-0 text-xs pt-0.5">{label}</span>
        <span className="text-manolo-text">{display}</span>
      </div>
    )
  }

  function Secao({ titulo, children }: { titulo: string; children: React.ReactNode }) {
    return (
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-manolo-muted mb-2">{titulo}</h3>
        <div className="space-y-1.5 pl-2 border-l-2 border-neutral-border">{children}</div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div className="relative card w-full max-w-2xl max-h-[85vh] flex flex-col animate-slide-up">
        {/* Header do modal */}
        <div className="flex items-center justify-between p-5 border-b border-neutral-border">
          <div>
            <h2 className="font-semibold text-manolo-text capitalize">{detalhe ? formatData(detalhe.data) : '...'}</h2>
            {detalhe?.resumo_dia && (
              <span className={`badge mt-1 ${RESUMO_CLASS[detalhe.resumo_dia]}`}>
                {RESUMO_LABEL[detalhe.resumo_dia]}
              </span>
            )}
          </div>
          <button onClick={onClose} className="btn-ghost p-1.5">✕</button>
        </div>

        {/* Corpo do modal */}
        <div className="overflow-y-auto p-5 space-y-5 flex-1">
          {loading && <p className="text-manolo-muted text-sm animate-pulse-soft">Carregando...</p>}
          {detalhe && (
            <>
              {detalhe.secoes.sono && (
                <Secao titulo="🌙 Sono">
                  <CampoSec label="Dormiu às" val={detalhe.secoes.sono.dormiu_as} />
                  <CampoSec label="Acordou às" val={detalhe.secoes.sono.acordou_as} />
                  <CampoSec label="Acordou à noite" val={detalhe.secoes.sono.acordou_noite} />
                  <CampoSec label="Cochilo" val={detalhe.secoes.sono.cochilo} />
                  <CampoSec label="Notas" val={detalhe.secoes.sono.notas} />
                </Secao>
              )}
              {detalhe.secoes.comunicacao && (
                <Secao titulo="💬 Comunicação">
                  <CampoSec label="Usou gestos" val={detalhe.secoes.comunicacao.usou_gestos} />
                  <CampoSec label="Palavras ditas" val={detalhe.secoes.comunicacao.palavras_ditas} />
                  <CampoSec label="Apontou" val={detalhe.secoes.comunicacao.apontou} />
                  <CampoSec label="Puxou a mão" val={detalhe.secoes.comunicacao.puxou_mao} />
                  <CampoSec label="Respondeu o nome" val={detalhe.secoes.comunicacao.respondeu_nome} />
                  <CampoSec label="Imitou" val={detalhe.secoes.comunicacao.imitou} />
                </Secao>
              )}
              {detalhe.secoes.alimentacao && (
                <Secao titulo="🍽️ Alimentação">
                  <CampoSec label="Comeu bem" val={detalhe.secoes.alimentacao.comeu_bem} />
                  <CampoSec label="Aceitou" val={detalhe.secoes.alimentacao.aceitou} />
                  <CampoSec label="Recusou" val={detalhe.secoes.alimentacao.recusou} />
                  <CampoSec label="Comeu sentado" val={detalhe.secoes.alimentacao.comeu_sentado} />
                  <CampoSec label="Utensílio" val={detalhe.secoes.alimentacao.utensilio} />
                </Secao>
              )}
              {detalhe.secoes.humor && (
                <Secao titulo="😊 Humor">
                  <CampoSec label="Humor geral" val={detalhe.secoes.humor.humor_geral} />
                  <CampoSec label="Teve crise" val={detalhe.secoes.humor.teve_crise} />
                  <CampoSec label="O que acalmou" val={detalhe.secoes.humor.o_que_acalmou} />
                  <CampoSec label="Notas" val={detalhe.secoes.humor.notas} />
                </Secao>
              )}
              {detalhe.secoes.brincar && (
                <Secao titulo="🎮 Brincar">
                  <CampoSec label="Com que brincou" val={detalhe.secoes.brincar.com_que_brincou} />
                  <CampoSec label="Modo" val={detalhe.secoes.brincar.modo} />
                  <CampoSec label="Faz-de-conta" val={detalhe.secoes.brincar.fez_faz_de_conta} />
                  <CampoSec label="Tempo sem tela" val={detalhe.secoes.brincar.tempo_sem_tela_minutos != null ? `${detalhe.secoes.brincar.tempo_sem_tela_minutos} min` : null} />
                </Secao>
              )}
              {detalhe.secoes.higiene && (
                <Secao titulo="🚿 Higiene">
                  <CampoSec label="Banho" val={detalhe.secoes.higiene.banho} />
                  <CampoSec label="Escovou dentes" val={detalhe.secoes.higiene.escovou_dentes} />
                  <CampoSec label="Sinalizou banheiro" val={detalhe.secoes.higiene.sinalizou_banheiro} />
                </Secao>
              )}
              {detalhe.secoes.rotina && (
                <Secao titulo="📋 Rotina">
                  <CampoSec label="Guardou brinquedos" val={detalhe.secoes.rotina.guardou_brinquedos} />
                  <CampoSec label="Ajudou em tarefa" val={detalhe.secoes.rotina.ajudou_tarefa} />
                  <CampoSec label="Aceitou transições" val={detalhe.secoes.rotina.aceitou_transicao} />
                </Secao>
              )}
              {detalhe.secoes.observacoes && (
                <Secao titulo="📝 Observações livres">
                  <CampoSec label="Conquistas" val={detalhe.secoes.observacoes.conquistas} />
                  <CampoSec label="Dificuldades" val={detalhe.secoes.observacoes.dificuldades} />
                  <CampoSec label="Diferente hoje" val={detalhe.secoes.observacoes.diferente_hoje} />
                </Secao>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// ============================================================
// PÁGINA
// ============================================================

export default function ChecklistsPage() {
  const [checklists, setChecklists] = useState<ChecklistResumo[]>([])
  const [total, setTotal] = useState(0)
  const [pagina, setPagina] = useState(1)
  const [loading, setLoading] = useState(true)
  const [selecionado, setSelecionado] = useState<string | null>(null)
  const [criancaId] = useState(getCriancaSelecionada)

  const POR_PAGINA = 20

  useEffect(() => {
    setLoading(true)
    getChecklists(criancaId, { pagina, por_pagina: POR_PAGINA })
      .then(r => { setChecklists(r.checklists); setTotal(r.total) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [pagina, criancaId])

  const totalPaginas = Math.ceil(total / POR_PAGINA)

  return (
    <>
      <Header titulo="Checklists" subtitulo={`${total} registros encontrados`} />

      <div className="p-4 md:p-6">
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-primary-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary uppercase tracking-wide">Data</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary uppercase tracking-wide hidden sm:table-cell">Resumo</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary uppercase tracking-wide hidden md:table-cell">Sono</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary uppercase tracking-wide hidden lg:table-cell">Comunicação</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary uppercase tracking-wide hidden lg:table-cell">Humor</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary uppercase tracking-wide">Origem</th>
              </tr>
            </thead>
            <tbody>
              {loading && [...Array(8)].map((_, i) => (
                <tr key={i} className="border-b border-neutral-border">
                  {[...Array(6)].map((_, j) => (
                    <td key={j} className="px-4 py-3"><div className="skeleton h-4 rounded" /></td>
                  ))}
                </tr>
              ))}

              {!loading && checklists.map(c => (
                <tr
                  key={c.id}
                  className="table-row"
                  onClick={() => setSelecionado(c.data)}
                >
                  <td className="px-4 py-3 font-medium text-manolo-text whitespace-nowrap">
                    {format(new Date(c.data + 'T12:00:00'), 'dd/MM/yyyy')}
                  </td>
                  <td className="px-4 py-3 hidden sm:table-cell">
                    {c.resumo_dia ? (
                      <span className={`badge ${RESUMO_CLASS[c.resumo_dia]}`}>
                        {RESUMO_LABEL[c.resumo_dia]}
                      </span>
                    ) : <span className="text-manolo-muted">—</span>}
                  </td>
                  <td className="px-4 py-3 text-manolo-muted hidden md:table-cell">
                    {c.dormiu_as && c.acordou_as ? `${c.dormiu_as} – ${c.acordou_as}` : '—'}
                  </td>
                  <td className="px-4 py-3 hidden lg:table-cell">
                    {c.palavras_ditas?.length ? (
                      <span className="text-primary text-xs">{c.palavras_ditas.slice(0, 3).join(', ')}</span>
                    ) : <span className="text-manolo-muted">—</span>}
                  </td>
                  <td className="px-4 py-3 hidden lg:table-cell">
                    {c.teve_crise && <span className="badge badge-red">Crise</span>}
                    {c.humor_geral && !c.teve_crise && <span className="text-xs text-manolo-muted">{c.humor_geral}</span>}
                    {!c.humor_geral && <span className="text-manolo-muted">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    <span className="badge badge-gray text-xs">{c.origem?.replace('whatsapp_', '') ?? '—'}</span>
                  </td>
                </tr>
              ))}

              {!loading && checklists.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-manolo-muted">
                    Nenhum checklist encontrado.
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          {/* Paginação */}
          {totalPaginas > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-neutral-border">
              <span className="text-xs text-manolo-muted">
                Página {pagina} de {totalPaginas} · {total} registros
              </span>
              <div className="flex gap-2">
                <button
                  className="btn-secondary py-1 px-3 text-xs"
                  disabled={pagina === 1}
                  onClick={() => setPagina(p => p - 1)}
                >
                  ← Anterior
                </button>
                <button
                  className="btn-secondary py-1 px-3 text-xs"
                  disabled={pagina === totalPaginas}
                  onClick={() => setPagina(p => p + 1)}
                >
                  Próxima →
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Modal de detalhe */}
      {selecionado && (
        <ModalChecklist
          data={selecionado}
          criancaId={criancaId}
          onClose={() => setSelecionado(null)}
        />
      )}
    </>
  )
}
