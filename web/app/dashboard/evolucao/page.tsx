'use client'

import { useEffect, useState, useMemo } from 'react'
import { Header } from '@/components/layout/Header'
import { getChecklists } from '@/lib/api'
import { getCriancaSelecionada } from '@/lib/auth'
import type { ChecklistResumo, PeriodoFiltro } from '@/types/manolo'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, ReferenceLine
} from 'recharts'
import { format, subDays } from 'date-fns'
import { ptBR } from 'date-fns/locale'

// ============================================================
// HELPERS
// ============================================================

function calcularPeriodo(filtro: PeriodoFiltro): { inicio: string; fim: string } {
  const fim = format(new Date(), 'yyyy-MM-dd')
  const dias = filtro === '7d' ? 7 : filtro === '30d' ? 30 : 90
  const inicio = format(subDays(new Date(), dias), 'yyyy-MM-dd')
  return { inicio, fim }
}

function horaParaDecimal(hora?: string): number | null {
  if (!hora) return null
  const [h, m] = hora.split(':').map(Number)
  return h + m / 60
}

function horaParaDecimalContinuo(hora?: string): number | null {
  if (!hora) return null
  const [h, m] = hora.split(':').map(Number)
  let decimal = h + m / 60
  if (decimal < 12) decimal += 24 // Trata madrugada (ex: 01:00 vira 25.0)
  return decimal
}

function calcularHorasSono(c: ChecklistResumo): number | null {
  if (!c.dormiu_as || !c.acordou_as) return null
  const dormiu = horaParaDecimal(c.dormiu_as)
  const acordou = horaParaDecimal(c.acordou_as)
  if (dormiu === null || acordou === null) return null
  const diff = acordou < dormiu ? acordou + 24 - dormiu : acordou - dormiu
  return Math.round(diff * 10) / 10
}

// ============================================================
// GRÁFICO BASE
// ============================================================

interface GraficoProps {
  dados: Record<string, unknown>[]
  linhas: { dataKey: string; nome: string; cor: string }[]
  yLabel?: string
  metaLinha?: { y: number; label: string; stroke?: string }
  yTickFormatter?: (value: any) => string
  tooltipFormatter?: (value: any, name: string) => [string, string]
  yDomain?: any[]
  yReversed?: boolean
}

function Grafico({ dados, linhas, yLabel, metaLinha, yTickFormatter, tooltipFormatter, yDomain, yReversed }: GraficoProps) {
  if (!dados.length) {
    return (
      <div className="h-40 flex items-center justify-center text-manolo-muted text-sm">
        Sem dados no período
      </div>
    )
  }
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={dados} margin={{ top: 8, right: 8, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="data" tick={{ fontSize: 11 }} />
        <YAxis 
          tickFormatter={yTickFormatter} 
          tick={{ fontSize: 11 }} 
          domain={yDomain || ['auto', 'auto']}
          reversed={yReversed}
          label={yLabel ? { value: yLabel, angle: -90, position: 'insideLeft', fontSize: 10 } : undefined} 
        />
        <Tooltip
          formatter={tooltipFormatter}
          contentStyle={{
            background: '#fff',
            border: '1px solid #E8E4DE',
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Legend iconType="circle" iconSize={8} />
        {metaLinha && (
          <ReferenceLine y={metaLinha.y} stroke={metaLinha.stroke || "#e11d48"} strokeDasharray="3 3" label={{ position: 'insideTopLeft', value: metaLinha.label, fill: metaLinha.stroke || "#e11d48", fontSize: 12 }} />
        )}
        {linhas.map(l => (
          <Line
            key={l.dataKey}
            type="monotone"
            dataKey={l.dataKey}
            name={l.nome}
            stroke={l.cor}
            strokeWidth={2}
            dot={{ r: 3, fill: l.cor }}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

// ============================================================
// SEÇÃO DE GRÁFICO
// ============================================================

function SecaoGrafico({ titulo, emoji, children }: { titulo: string; emoji: string; children: React.ReactNode }) {
  return (
    <div className="card p-5 space-y-4 animate-fade-in">
      <h2 className="section-title flex items-center gap-2">
        <span>{emoji}</span> {titulo}
      </h2>
      {children}
    </div>
  )
}

// ============================================================
// PÁGINA
// ============================================================

const PERIODOS: { label: string; value: PeriodoFiltro }[] = [
  { label: '7 dias', value: '7d' },
  { label: '30 dias', value: '30d' },
  { label: '90 dias', value: '90d' },
]

export default function EvolucaoPage() {
  const [checklists, setChecklists] = useState<ChecklistResumo[]>([])
  const [periodo, setPeriodo] = useState<PeriodoFiltro>('30d')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const criancaId = getCriancaSelecionada()
    const { inicio, fim } = calcularPeriodo(periodo)
    setLoading(true)
    getChecklists(criancaId, { inicio, fim, por_pagina: 90 })
      .then(r => setChecklists(r.checklists))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [periodo])

  // Ordenar por data ascendente para os gráficos
  const dados = useMemo(() =>
    [...checklists].sort((a, b) => a.data.localeCompare(b.data)),
    [checklists]
  )

  const formatData = (iso: string) =>
    format(new Date(iso + 'T12:00:00'), 'd/MM', { locale: ptBR })

  const dadosSono = useMemo(() =>
    dados.map(c => ({
      data: formatData(c.data),
      'Horas de sono': calcularHorasSono(c),
      'Dormiu às': horaParaDecimalContinuo(c.dormiu_as),
      'Acordou à noite': c.acordou_noite ? 1 : 0,
    })),
    [dados]
  )

  const dadosTela = useMemo(() =>
    dados.map(c => ({
      data: formatData(c.data),
      'Tempo de tela': c.tempo_tela_minutos != null ? c.tempo_tela_minutos / 60 : null,
    })),
    [dados]
  )

  const dadosComunicacao = useMemo(() =>
    dados.map(c => ({
      data: formatData(c.data),
      'Palavras ditas': c.palavras_ditas?.length ?? null,
      'Usou gestos': c.usou_gestos ? 1 : 0,
    })),
    [dados]
  )

  const dadosHumor = useMemo(() => {
    const humorMap: Record<string, number> = {
      muito_bom: 5, bom: 4, regular: 3, agitado: 2, 'difícil': 1,
    }
    return dados.map(c => ({
      data: formatData(c.data),
      'Humor (1-5)': c.humor_geral ? humorMap[c.humor_geral] ?? null : null,
      'Crise': c.teve_crise ? 1 : 0,
    }))
  }, [dados])

  const dadosBrincar = useMemo(() =>
    dados.map(c => ({
      data: formatData(c.data),
      'Tempo sem tela (min)': c.tempo_sem_tela_minutos ?? null,
    })),
    [dados]
  )

  return (
    <>
      <Header titulo="Evolução" subtitulo="Séries temporais dos checklists diários" />

      <div className="p-4 md:p-6 space-y-5">

        {/* Filtro de período */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm text-manolo-muted">Período:</span>
          {PERIODOS.map(p => (
            <button
              key={p.value}
              onClick={() => setPeriodo(p.value)}
              className={
                periodo === p.value
                  ? 'btn-primary py-1.5 px-3 text-xs'
                  : 'btn-secondary py-1.5 px-3 text-xs'
              }
            >
              {p.label}
            </button>
          ))}
          {loading && <span className="text-xs text-manolo-muted animate-pulse-soft">Carregando...</span>}
        </div>

        {/* Gráficos */}
        <SecaoGrafico titulo="Sono" emoji="🌙">
          <Grafico
            dados={dadosSono}
            linhas={[
              { dataKey: 'Horas de sono', nome: 'Horas de sono', cor: '#2D6A4F' },
              { dataKey: 'Acordou à noite', nome: 'Acordou à noite (0/1)', cor: '#7C8C99' },
            ]}
            yLabel="horas"
          />
        </SecaoGrafico>

        <SecaoGrafico titulo="Horário de Dormir" emoji="⏰">
          <Grafico
            dados={dadosSono}
            linhas={[
              { dataKey: 'Dormiu às', nome: 'Dormiu às', cor: '#E63946' },
            ]}
            metaLinha={{ y: 20.5, label: "Meta (20:30)", stroke: "#2D6A4F" }}
            yDomain={[19.0, 'auto']}
            yReversed={true}
            yTickFormatter={(val: number) => {
              let h = Math.floor(val)
              if (h >= 24) h -= 24
              const m = Math.round((val - Math.floor(val)) * 60)
              return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`
            }}
            tooltipFormatter={(val: any, name: string) => {
              if (typeof val === 'number') {
                let h = Math.floor(val)
                if (h >= 24) h -= 24
                const m = Math.round((val - Math.floor(val)) * 60)
                return [`${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`, name]
              }
              return [val, name]
            }}
          />
        </SecaoGrafico>

        <SecaoGrafico titulo="Uso de Telas" emoji="📱">
          <Grafico
            dados={dadosTela}
            linhas={[
              { dataKey: 'Tempo de tela', nome: 'Tempo de tela', cor: '#B5451B' },
            ]}
            yTickFormatter={(val: number) => {
              const h = Math.floor(val)
              const m = Math.round((val - h) * 60)
              if (h === 0) return `${m}m`
              return `${h}h${m.toString().padStart(2, '0')}m`
            }}
            tooltipFormatter={(val: any, name: string) => {
              if (typeof val === 'number') {
                const h = Math.floor(val)
                const m = Math.round((val - h) * 60)
                if (h === 0) return [`${m}m`, name]
                return [`${h}h${m.toString().padStart(2, '0')}m`, name]
              }
              return [val, name]
            }}
          />
        </SecaoGrafico>

        <SecaoGrafico titulo="Comunicação" emoji="💬">
          <Grafico
            dados={dadosComunicacao}
            linhas={[
              { dataKey: 'Palavras ditas', nome: 'Palavras ditas', cor: '#2D6A4F' },
              { dataKey: 'Usou gestos', nome: 'Gestos (0/1)', cor: '#52B788' },
            ]}
          />
        </SecaoGrafico>

        <SecaoGrafico titulo="Humor e regulação" emoji="🧘">
          <Grafico
            dados={dadosHumor}
            linhas={[
              { dataKey: 'Humor (1-5)', nome: 'Humor geral (1=difícil, 5=muito bom)', cor: '#2D6A4F' },
              { dataKey: 'Crise', nome: 'Crise (0/1)', cor: '#B5451B' },
            ]}
          />
        </SecaoGrafico>

        <SecaoGrafico titulo="Brincar" emoji="🎮">
          <Grafico
            dados={dadosBrincar}
            linhas={[
              { dataKey: 'Tempo sem tela (min)', nome: 'Tempo sem tela (min)', cor: '#52B788' },
            ]}
            yLabel="min"
          />
        </SecaoGrafico>

      </div>
    </>
  )
}
