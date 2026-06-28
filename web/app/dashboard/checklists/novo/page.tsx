'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { getCriancaSelecionada } from '@/lib/auth'
import { apiFetch } from '@/lib/api'
import { TagInput } from '@/components/ui/TagInput'
import { Toggle } from '@/components/ui/Toggle'
import { 
  IconMoon, IconDeviceTv, IconSoup, IconPuzzle, 
  IconMessageCircle, IconBath, IconShirt, IconActivity, 
  IconSmile, IconClock, IconFileText, IconCheck, IconChevronDown, IconChevronUp 
} from '@tabler/icons-react'

// Estrutura de Estado Padrão
const DEFAULT_STATE = {
  data: new Date().toISOString().split('T')[0],
  resumo_dia: '',
  sono: { dormiu_as: '', acordou_as: '', acordou_noite: false, cochilo: false, notas: '' },
  tela: { usou_tela: false, tempo_minutos: 0, conteudo: '', reacao_retirada: '' },
  alimentacao: { comeu_bem: false, aceitou: [], recusou: [], comeu_sentado: false, utensilio: '' },
  comunicacao: { usou_gestos: false, palavras_ditas: [], apontou: false, puxou_mao: '', respondeu_nome: '', imitou: false },
  brincar: { com_que_brincou: [], modo: '', fez_faz_de_conta: false, tempo_sem_tela_minutos: 0 },
  higiene: { banho: '', escovou_dentes: false, sinalizou_banheiro: false },
  vestuario: { colaborou_roupa: false, incomodo_sensorial: false },
  movimento: { atividades: [], caiu_muito: false, buscou_colo: false },
  humor: { humor_geral: '', teve_crise: false, o_que_acalmou: '', cobertor_disponivel: false, se_acalmou_sem_cobertor: false, notas: '' },
  rotina: { guardou_brinquedos: false, ajudou_tarefa: false, aceitou_transicao: false },
  observacoes: { conquistas: '', dificuldades: '', diferente_hoje: '' }
}

// Componente Card de Seção Colapsável
function SectionCard({ title, icon: Icon, isPartial, children }: any) {
  const [isOpen, setIsOpen] = useState(false)
  return (
    <div className="card overflow-hidden transition-all duration-300">
      <div 
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-neutral-bg/50"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${isPartial ? 'bg-primary/20 text-primary-dark' : 'bg-neutral-bg text-manolo-muted'}`}>
            <Icon className="w-5 h-5" />
          </div>
          <h3 className="font-semibold text-manolo-text">{title}</h3>
          {isPartial && <span className="text-[10px] uppercase font-bold bg-secondary/30 text-secondary-dark px-2 py-0.5 rounded-full">Parcial Salvo</span>}
        </div>
        {isOpen ? <IconChevronUp className="w-5 h-5 text-manolo-muted" /> : <IconChevronDown className="w-5 h-5 text-manolo-muted" />}
      </div>
      {isOpen && (
        <div className="p-4 pt-0 border-t border-neutral-border/50 bg-neutral-bg/10 animate-fade-in space-y-4">
          {children}
        </div>
      )}
    </div>
  )
}

export default function ChecklistNovoPage() {
  const router = useRouter()
  const criancaId = getCriancaSelecionada()
  
  const [form, setForm] = useState(DEFAULT_STATE)
  const [status, setStatus] = useState<'idle' | 'loading' | 'saving' | 'saved' | 'error'>('idle')
  const [isEditMode, setIsEditMode] = useState(false)
  const [loadedSections, setLoadedSections] = useState<string[]>([])

  // Carrega rascunho do LocalStorage apenas na montagem
  useEffect(() => {
    const draft = localStorage.getItem(`checklist_rascunho_${form.data}`)
    if (draft) {
      try {
        const parsed = JSON.parse(draft)
        setForm(prev => ({ ...prev, ...parsed }))
      } catch (e) {}
    }
  }, [])

  // Auto-save no LocalStorage (debounced)
  useEffect(() => {
    if (status === 'idle' || status === 'error') {
      const timer = setTimeout(() => {
        localStorage.setItem(`checklist_rascunho_${form.data}`, JSON.stringify(form))
      }, 1000)
      return () => clearTimeout(timer)
    }
  }, [form, status])

  // Busca dados remotos se existirem
  const fetchExistente = useCallback(async (data: string) => {
    if (!criancaId) return
    setStatus('loading')
    try {
      const res: any = await apiFetch(`/api/checklists/${criancaId}/${data}`)
      if (res && res.id) {
        setIsEditMode(true)
        // Merge state from DB
        const dbState: any = { data: res.data, resumo_dia: res.resumo_dia || '' }
        const secs = []
        for (const [secName, secData] of Object.entries(res.secoes || {})) {
          if (secData) {
            dbState[secName] = { ...DEFAULT_STATE[secName as keyof typeof DEFAULT_STATE], ...secData }
            secs.push(secName)
          }
        }
        setLoadedSections(secs)
        setForm(prev => ({ ...prev, ...dbState }))
      }
    } catch (e: any) {
      if (e.status === 404) {
        setIsEditMode(false)
        setLoadedSections([])
        // Mantém o estado atual (pode ser rascunho)
      }
    } finally {
      setStatus('idle')
    }
  }, [criancaId])

  useEffect(() => {
    fetchExistente(form.data)
  }, [form.data, fetchExistente])

  const updateSection = (section: keyof typeof DEFAULT_STATE, field: string, value: any) => {
    setForm(prev => ({
      ...prev,
      [section]: {
        ...(prev[section] as any),
        [field]: value
      }
    }))
  }

  const handleSave = async () => {
    setStatus('saving')
    try {
      if (isEditMode) {
        await apiFetch(`/api/checklists/${criancaId}/${form.data}`, {
          method: 'PATCH',
          body: JSON.stringify(form)
        })
      } else {
        await apiFetch(`/api/checklists/${criancaId}`, {
          method: 'POST',
          body: JSON.stringify(form)
        })
      }
      setStatus('saved')
      localStorage.removeItem(`checklist_rascunho_${form.data}`)
      setTimeout(() => router.push('/dashboard/checklists'), 1500)
    } catch (error) {
      console.error(error)
      setStatus('error')
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6 pb-24">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-manolo-text flex items-center gap-2">
          <IconFileText className="text-primary" /> 
          Checklist Diário
        </h1>
        <input 
          type="date" 
          value={form.data}
          onChange={e => setForm(prev => ({ ...prev, data: e.target.value }))}
          className="input w-auto text-sm"
        />
      </div>

      <div className="space-y-4">
        {/* SONO */}
        <SectionCard title="Sono" icon={IconMoon} isPartial={loadedSections.includes('sono')}>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Dormiu às</label>
              <input type="time" className="input" value={form.sono.dormiu_as || ''} onChange={e => updateSection('sono', 'dormiu_as', e.target.value)} />
            </div>
            <div>
              <label className="label">Acordou às</label>
              <input type="time" className="input" value={form.sono.acordou_as || ''} onChange={e => updateSection('sono', 'acordou_as', e.target.value)} />
            </div>
          </div>
          <div className="flex gap-6">
            <Toggle label="Acordou na noite?" checked={form.sono.acordou_noite} onChange={v => updateSection('sono', 'acordou_noite', v)} />
            <Toggle label="Tirou cochilo?" checked={form.sono.cochilo} onChange={v => updateSection('sono', 'cochilo', v)} />
          </div>
          <div>
            <label className="label">Notas sobre o sono</label>
            <input type="text" className="input" placeholder="Opcional..." value={form.sono.notas || ''} onChange={e => updateSection('sono', 'notas', e.target.value)} />
          </div>
        </SectionCard>

        {/* ALIMENTACAO */}
        <SectionCard title="Alimentação" icon={IconSoup} isPartial={loadedSections.includes('alimentacao')}>
          <div className="flex gap-6 mb-4">
            <Toggle label="Comeu bem?" checked={form.alimentacao.comeu_bem} onChange={v => updateSection('alimentacao', 'comeu_bem', v)} />
            <Toggle label="Comeu sentado?" checked={form.alimentacao.comeu_sentado} onChange={v => updateSection('alimentacao', 'comeu_sentado', v)} />
          </div>
          <div className="grid grid-cols-1 gap-4">
            <div>
              <label className="label">O que aceitou?</label>
              <TagInput tags={form.alimentacao.aceitou} onChange={v => updateSection('alimentacao', 'aceitou', v)} placeholder="Ex: Arroz, Maçã..." />
            </div>
            <div>
              <label className="label">O que recusou?</label>
              <TagInput tags={form.alimentacao.recusou} onChange={v => updateSection('alimentacao', 'recusou', v)} placeholder="Ex: Feijão, Carne..." />
            </div>
            <div>
              <label className="label">Utensílio principal</label>
              <select className="input" value={form.alimentacao.utensilio || ''} onChange={e => updateSection('alimentacao', 'utensilio', e.target.value)}>
                <option value="">Selecione...</option>
                <option value="colher">Colher</option>
                <option value="garfo">Garfo</option>
                <option value="mao">Mão</option>
                <option value="misto">Misto</option>
              </select>
            </div>
          </div>
        </SectionCard>

        {/* COMUNICAÇÃO */}
        <SectionCard title="Comunicação" icon={IconMessageCircle} isPartial={loadedSections.includes('comunicacao')}>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <Toggle label="Usou gestos?" checked={form.comunicacao.usou_gestos} onChange={v => updateSection('comunicacao', 'usou_gestos', v)} />
            <Toggle label="Apontou?" checked={form.comunicacao.apontou} onChange={v => updateSection('comunicacao', 'apontou', v)} />
            <Toggle label="Imitou som/ação?" checked={form.comunicacao.imitou} onChange={v => updateSection('comunicacao', 'imitou', v)} />
          </div>
          <div>
            <label className="label">Palavras ditas</label>
            <TagInput tags={form.comunicacao.palavras_ditas} onChange={v => updateSection('comunicacao', 'palavras_ditas', v)} placeholder="Ex: Água, Mamãe..." />
          </div>
          <div className="grid grid-cols-2 gap-4 mt-4">
            <div>
              <label className="label">Puxou a mão para pedir?</label>
              <select className="input" value={form.comunicacao.puxou_mao || ''} onChange={e => updateSection('comunicacao', 'puxou_mao', e.target.value)}>
                <option value="">Selecione...</option>
                <option value="nunca">Nunca</option>
                <option value="às_vezes">Às vezes</option>
                <option value="maioria">Maioria das vezes</option>
                <option value="sempre">Sempre</option>
              </select>
            </div>
            <div>
              <label className="label">Respondeu ao nome?</label>
              <select className="input" value={form.comunicacao.respondeu_nome || ''} onChange={e => updateSection('comunicacao', 'respondeu_nome', e.target.value)}>
                <option value="">Selecione...</option>
                <option value="nunca">Nunca</option>
                <option value="às_vezes">Às vezes</option>
                <option value="sempre">Sempre</option>
              </select>
            </div>
          </div>
        </SectionCard>

        {/* BRINCAR */}
        <SectionCard title="Brincar" icon={IconPuzzle} isPartial={loadedSections.includes('brincar')}>
          <div className="flex gap-6 mb-4">
            <Toggle label="Fez faz-de-conta?" checked={form.brincar.fez_faz_de_conta} onChange={v => updateSection('brincar', 'fez_faz_de_conta', v)} />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label">Com que brincou?</label>
              <TagInput tags={form.brincar.com_que_brincou} onChange={v => updateSection('brincar', 'com_que_brincou', v)} placeholder="Ex: Carrinho, Blocos..." />
            </div>
            <div>
              <label className="label">Modo de brincar</label>
              <select className="input" value={form.brincar.modo || ''} onChange={e => updateSection('brincar', 'modo', e.target.value)}>
                <option value="">Selecione...</option>
                <option value="sozinho">Sozinho</option>
                <option value="com_adulto">Com adulto</option>
                <option value="misto">Misto</option>
              </select>
            </div>
            <div>
              <label className="label">Tempo brincando sem tela (minutos)</label>
              <input type="number" className="input" value={form.brincar.tempo_sem_tela_minutos || 0} onChange={e => updateSection('brincar', 'tempo_sem_tela_minutos', parseInt(e.target.value) || 0)} />
            </div>
          </div>
        </SectionCard>

        {/* HUMOR */}
        <SectionCard title="Humor e Regulação" icon={IconSmile} isPartial={loadedSections.includes('humor')}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="label">Humor Geral</label>
              <select className="input" value={form.humor.humor_geral || ''} onChange={e => updateSection('humor', 'humor_geral', e.target.value)}>
                <option value="">Selecione...</option>
                <option value="muito_bom">Muito Bom</option>
                <option value="bom">Bom</option>
                <option value="regular">Regular</option>
                <option value="agitado">Agitado</option>
                <option value="difícil">Difícil</option>
              </select>
            </div>
            <div className="flex items-center">
              <Toggle label="Teve crise/meltdown?" checked={form.humor.teve_crise} onChange={v => updateSection('humor', 'teve_crise', v)} />
            </div>
          </div>
          {form.humor.teve_crise && (
            <div className="mb-4">
              <label className="label">O que acalmou?</label>
              <input type="text" className="input" value={form.humor.o_que_acalmou || ''} onChange={e => updateSection('humor', 'o_que_acalmou', e.target.value)} />
            </div>
          )}
          <div className="flex gap-6 mb-4">
             <Toggle label="Cobertor disponível?" checked={form.humor.cobertor_disponivel} onChange={v => updateSection('humor', 'cobertor_disponivel', v)} />
             <Toggle label="Acalmou sem cobertor?" checked={form.humor.se_acalmou_sem_cobertor} onChange={v => updateSection('humor', 'se_acalmou_sem_cobertor', v)} />
          </div>
          <div>
            <label className="label">Notas</label>
            <textarea className="input min-h-[60px]" value={form.humor.notas || ''} onChange={e => updateSection('humor', 'notas', e.target.value)}></textarea>
          </div>
        </SectionCard>

        {/* TELA */}
        <SectionCard title="Uso de Telas" icon={IconDeviceTv} isPartial={loadedSections.includes('tela')}>
          <div className="mb-4">
            <Toggle label="Usou telas hoje?" checked={form.tela.usou_tela} onChange={v => updateSection('tela', 'usou_tela', v)} />
          </div>
          {form.tela.usou_tela && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="label">Tempo (min)</label>
                <input type="number" className="input" value={form.tela.tempo_minutos || 0} onChange={e => updateSection('tela', 'tempo_minutos', parseInt(e.target.value) || 0)} />
              </div>
              <div>
                <label className="label">Conteúdo</label>
                <input type="text" className="input" placeholder="Ex: Peppa..." value={form.tela.conteudo || ''} onChange={e => updateSection('tela', 'conteudo', e.target.value)} />
              </div>
              <div>
                <label className="label">Reação ao desligar</label>
                <select className="input" value={form.tela.reacao_retirada || ''} onChange={e => updateSection('tela', 'reacao_retirada', e.target.value)}>
                  <option value="">Selecione...</option>
                  <option value="tranquilo">Tranquilo</option>
                  <option value="resistencia">Resistência</option>
                  <option value="crise">Crise</option>
                </select>
              </div>
            </div>
          )}
        </SectionCard>
        
        {/* OUTROS: Higiene, Vestuário, Movimento, Rotina, Observações */}
        <SectionCard title="Outros (Higiene, Vestuário, Movimento...)" icon={IconActivity} isPartial={loadedSections.includes('higiene')}>
           <div className="space-y-6">
              {/* Higiene */}
              <div>
                <h4 className="text-sm font-semibold mb-2">Higiene</h4>
                <div className="flex gap-4">
                  <Toggle label="Escovou dentes?" checked={form.higiene.escovou_dentes} onChange={v => updateSection('higiene', 'escovou_dentes', v)} />
                  <Toggle label="Sinalizou banheiro?" checked={form.higiene.sinalizou_banheiro} onChange={v => updateSection('higiene', 'sinalizou_banheiro', v)} />
                </div>
              </div>
              {/* Vestuario */}
              <div>
                <h4 className="text-sm font-semibold mb-2">Vestuário</h4>
                <div className="flex gap-4">
                  <Toggle label="Colaborou ao vestir?" checked={form.vestuario.colaborou_roupa} onChange={v => updateSection('vestuario', 'colaborou_roupa', v)} />
                  <Toggle label="Incômodo sensorial (etiqueta/tecido)?" checked={form.vestuario.incomodo_sensorial} onChange={v => updateSection('vestuario', 'incomodo_sensorial', v)} />
                </div>
              </div>
              {/* Rotina */}
              <div>
                <h4 className="text-sm font-semibold mb-2">Rotina</h4>
                <div className="flex flex-wrap gap-4">
                  <Toggle label="Guardou brinquedos?" checked={form.rotina.guardou_brinquedos} onChange={v => updateSection('rotina', 'guardou_brinquedos', v)} />
                  <Toggle label="Ajudou tarefa?" checked={form.rotina.ajudou_tarefa} onChange={v => updateSection('rotina', 'ajudou_tarefa', v)} />
                  <Toggle label="Aceitou transição?" checked={form.rotina.aceitou_transicao} onChange={v => updateSection('rotina', 'aceitou_transicao', v)} />
                </div>
              </div>
              {/* Observações */}
              <div>
                <h4 className="text-sm font-semibold mb-2">Observações Livres</h4>
                <div className="grid grid-cols-1 gap-3">
                   <input type="text" className="input" placeholder="Conquistas do dia..." value={form.observacoes.conquistas || ''} onChange={e => updateSection('observacoes', 'conquistas', e.target.value)} />
                   <input type="text" className="input" placeholder="Dificuldades do dia..." value={form.observacoes.dificuldades || ''} onChange={e => updateSection('observacoes', 'dificuldades', e.target.value)} />
                   <input type="text" className="input" placeholder="Algo diferente hoje?" value={form.observacoes.diferente_hoje || ''} onChange={e => updateSection('observacoes', 'diferente_hoje', e.target.value)} />
                </div>
              </div>
           </div>
        </SectionCard>

      </div>

      {/* FIXED BOTTOM BAR */}
      <div className="fixed bottom-0 left-0 right-0 md:left-64 bg-white border-t border-neutral-border p-4 shadow-lg z-10 flex items-center justify-between">
        <div className="flex items-center gap-4">
           <div>
             <label className="text-xs font-semibold block text-manolo-muted mb-1 uppercase tracking-wider">Avaliação Geral do Dia</label>
             <select 
               className="input py-1.5"
               value={form.resumo_dia}
               onChange={e => setForm(prev => ({ ...prev, resumo_dia: e.target.value }))}
             >
               <option value="">Selecione...</option>
               <option value="muito_bom">Muito Bom</option>
               <option value="bom">Bom</option>
               <option value="regular">Regular</option>
               <option value="difícil">Difícil</option>
             </select>
           </div>
        </div>
        
        <button 
          onClick={handleSave} 
          disabled={status === 'saving' || status === 'loading'}
          className="btn-primary min-w-[140px] flex items-center justify-center gap-2"
        >
          {status === 'saving' ? 'Salvando...' : status === 'saved' ? <><IconCheck className="w-5 h-5" /> Salvo</> : (isEditMode ? 'Atualizar Checklist' : 'Salvar Checklist')}
        </button>
      </div>
      
      {status === 'error' && (
        <div className="fixed bottom-24 left-1/2 transform -translate-x-1/2 bg-red-100 text-red-600 px-4 py-2 rounded-lg shadow border border-red-200">
          Erro ao salvar. Verifique a conexão e tente novamente.
        </div>
      )}
    </div>
  )
}
