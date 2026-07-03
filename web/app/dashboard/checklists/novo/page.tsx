'use client'

import { useState, useEffect, useCallback, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { getCriancaSelecionada } from '@/lib/auth'
import { apiFetch } from '@/lib/api'
import { TagInput } from '@/components/ui/TagInput'
import { SelectBoolean } from '@/components/ui/SelectBoolean'
import { 
  IconMoon, IconDeviceTv, IconSoup, IconPuzzle, 
  IconMessageCircle, IconBath, IconShirt, IconActivity, 
  IconMoodSmile, IconClock, IconFileText, IconCheck, IconChevronDown, IconChevronUp 
} from '@tabler/icons-react'

// Estrutura de Estado Padrão
const DEFAULT_STATE = {
  data: new Date().toISOString().split('T')[0],
  resumo_dia: '',
  sono: { dormiu_as: '', acordou_as: '', acordou_noite: false, cochilo_inicio: '', cochilo_fim: '', notas: '' },
  tela: { usou_tela: false, tempo_minutos: 0, conteudo: '', reacao_retirada: '' },
  alimentacao: { comeu_bem: false, aceitou: [], recusou: [], comeu_sentado: false, utensilio: '' },
  comunicacao: { usou_gestos: false, palavras_ditas: [], apontou: false, puxou_mao: '', respondeu_nome: '', imitou: false },
  brincar: { com_que_brincou: [], modo: '', fez_faz_de_conta: false, tempo_sem_tela_minutos: 0 },
  higiene: { banho: '', escovou_dentes: false, sinalizou_banheiro: false },
  vestuario: { colaborou_roupa: false, incomodo_sensorial: false },
  movimento: { atividades: [], caiu_muito: false, buscou_colo: false },
  humor: { humor_geral: '', teve_crise: false, o_que_acalmou: '', cobertor_disponivel: false, se_acalmou_sem_cobertor: false, notas: '' },
  rotina: { guardou_brinquedos: false, ajudou_tarefa: false, aceitou_transicao: false, teve_escola: false },
  observacoes: { conquistas: '', dificuldades: '', diferente_hoje: '' },
  sessoes_terapia: []
}

function getSectionStatus(section: string, form: typeof DEFAULT_STATE, loadedSections: string[]) {
  if (!loadedSections.includes(section)) return 'not_started'
  
  const data: any = form[section as keyof typeof form]
  let isComplete = true
  
  switch (section) {
    case 'sono':
      isComplete = !!(data.dormiu_as && data.acordou_as)
      break
    case 'tela':
      isComplete = !data.usou_tela || !!(data.tempo_minutos > 0 && data.conteudo && data.reacao_retirada)
      break
    case 'alimentacao':
      isComplete = !!data.utensilio
      break
    case 'comunicacao':
      isComplete = !!(data.puxou_mao && data.respondeu_nome)
      break
    case 'brincar':
      isComplete = !!data.modo
      break
    case 'higiene':
      isComplete = !!(
        data?.banho || data?.escovou_dentes || data?.sinalizou_banheiro ||
        form.vestuario?.colaborou_roupa || form.vestuario?.incomodo_sensorial ||
        form.rotina?.guardou_brinquedos || form.rotina?.ajudou_tarefa || form.rotina?.aceitou_transicao ||
        (form.movimento?.atividades && form.movimento.atividades.length > 0) ||
        form.observacoes?.conquistas || form.observacoes?.dificuldades || form.observacoes?.diferente_hoje
      )
      break
    case 'humor':
      isComplete = !!data.humor_geral
      break
    default:
      isComplete = true 
  }
  
  return isComplete ? 'complete' : 'incomplete'
}

// Componente Card de Seção Colapsável
function SectionCard({ title, icon: Icon, status, children }: any) {
  const [isOpen, setIsOpen] = useState(false)
  
  let statusBadge = null
  let iconColor = 'bg-neutral-bg text-manolo-muted'
  
  if (status === 'complete') {
    statusBadge = <span className="text-[10px] uppercase font-bold bg-green-500/20 text-green-700 px-2 py-0.5 rounded-full">Completo</span>
    iconColor = 'bg-green-500/20 text-green-700'
  } else if (status === 'incomplete') {
    statusBadge = <span className="text-[10px] uppercase font-bold bg-yellow-500/20 text-yellow-700 px-2 py-0.5 rounded-full">Incompleto</span>
    iconColor = 'bg-yellow-500/20 text-yellow-700'
  } else {
    statusBadge = <span className="text-[10px] uppercase font-bold bg-red-500/10 text-red-600 px-2 py-0.5 rounded-full">Não Iniciado</span>
    iconColor = 'bg-red-500/10 text-red-600'
  }

  return (
    <div className="card overflow-hidden transition-all duration-300">
      <div 
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-neutral-bg/50"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${iconColor}`}>
            <Icon className="w-5 h-5" />
          </div>
          <h3 className="font-semibold text-manolo-text">{title}</h3>
          {statusBadge}
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
  return (
    <Suspense fallback={<div className="p-8 text-center text-manolo-muted">Carregando formulário...</div>}>
      <ChecklistNovoContent />
    </Suspense>
  )
}

function ChecklistNovoContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const urlDate = searchParams.get('data')
  const criancaId = getCriancaSelecionada()
  
  const [form, setForm] = useState({ ...DEFAULT_STATE, data: urlDate || DEFAULT_STATE.data })
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
            if (secName === 'sessoes_terapia') {
              dbState[secName] = secData
            } else {
              dbState[secName] = { ...(DEFAULT_STATE[secName as keyof typeof DEFAULT_STATE] as any), ...(secData as any) }
            }
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
        <SectionCard title="Sono" icon={IconMoon} status={getSectionStatus('sono', form, loadedSections)}>
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
          <div className="flex gap-6 mb-4">
            <SelectBoolean label="Acordou na noite?" checked={form.sono.acordou_noite} onChange={v => updateSection('sono', 'acordou_noite', v)} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Início Cochilo</label>
              <input type="time" className="input" value={(form.sono as any).cochilo_inicio || ''} onChange={e => updateSection('sono', 'cochilo_inicio', e.target.value)} />
            </div>
            <div>
              <label className="label">Fim Cochilo</label>
              <input type="time" className="input" value={(form.sono as any).cochilo_fim || ''} onChange={e => updateSection('sono', 'cochilo_fim', e.target.value)} />
            </div>
          </div>
          <div>
            <label className="label">Notas sobre o sono</label>
            <input type="text" className="input" placeholder="Opcional..." value={form.sono.notas || ''} onChange={e => updateSection('sono', 'notas', e.target.value)} />
          </div>
        </SectionCard>

        {/* ALIMENTACAO */}
        <SectionCard title="Alimentação" icon={IconSoup} status={getSectionStatus('alimentacao', form, loadedSections)}>
          <div className="grid grid-cols-2 gap-6 mb-4">
            <SelectBoolean label="Comeu bem?" checked={form.alimentacao.comeu_bem} onChange={v => updateSection('alimentacao', 'comeu_bem', v)} />
            <SelectBoolean label="Comeu sentado?" checked={form.alimentacao.comeu_sentado} onChange={v => updateSection('alimentacao', 'comeu_sentado', v)} />
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
        <SectionCard title="Comunicação" icon={IconMessageCircle} status={getSectionStatus('comunicacao', form, loadedSections)}>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
            <SelectBoolean label="Usou gestos?" checked={form.comunicacao.usou_gestos} onChange={v => updateSection('comunicacao', 'usou_gestos', v)} />
            <SelectBoolean label="Apontou?" checked={form.comunicacao.apontou} onChange={v => updateSection('comunicacao', 'apontou', v)} />
            <SelectBoolean label="Imitou som/ação?" checked={form.comunicacao.imitou} onChange={v => updateSection('comunicacao', 'imitou', v)} />
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
        <SectionCard title="Brincar" icon={IconPuzzle} status={getSectionStatus('brincar', form, loadedSections)}>
          <div className="flex gap-6 mb-4">
            <SelectBoolean label="Fez faz-de-conta?" checked={form.brincar.fez_faz_de_conta} onChange={v => updateSection('brincar', 'fez_faz_de_conta', v)} />
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
        <SectionCard title="Humor e Regulação" icon={IconMoodSmile} status={getSectionStatus('humor', form, loadedSections)}>
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
            <div className="flex items-center mt-6">
              <SelectBoolean label="Teve crise/meltdown?" checked={form.humor.teve_crise} onChange={v => updateSection('humor', 'teve_crise', v)} />
            </div>
          </div>
          {form.humor.teve_crise && (
            <div className="mb-4">
              <label className="label">O que acalmou?</label>
              <input type="text" className="input" value={form.humor.o_que_acalmou || ''} onChange={e => updateSection('humor', 'o_que_acalmou', e.target.value)} />
            </div>
          )}
          <div className="grid grid-cols-2 gap-6 mb-4">
             <SelectBoolean label="Cobertor disponível?" checked={form.humor.cobertor_disponivel} onChange={v => updateSection('humor', 'cobertor_disponivel', v)} />
             <SelectBoolean label="Acalmou sem cobertor?" checked={form.humor.se_acalmou_sem_cobertor} onChange={v => updateSection('humor', 'se_acalmou_sem_cobertor', v)} />
          </div>
          <div>
            <label className="label">Notas</label>
            <textarea className="input min-h-[60px]" value={form.humor.notas || ''} onChange={e => updateSection('humor', 'notas', e.target.value)}></textarea>
          </div>
        </SectionCard>

        {/* TELA */}
        <SectionCard title="Uso de Telas" icon={IconDeviceTv} status={getSectionStatus('tela', form, loadedSections)}>
          <div className="mb-4">
            <SelectBoolean label="Usou telas hoje?" checked={form.tela.usou_tela} onChange={v => updateSection('tela', 'usou_tela', v)} />
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
        <SectionCard title="Outros (Higiene, Vestuário, Movimento...)" icon={IconActivity} status={getSectionStatus('higiene', form, loadedSections)}>
           <div className="space-y-6">
              {/* Higiene */}
              <div>
                <h4 className="text-sm font-semibold mb-2">Higiene</h4>
                <div className="grid grid-cols-2 gap-4">
                  <SelectBoolean label="Escovou dentes?" checked={form.higiene.escovou_dentes} onChange={v => updateSection('higiene', 'escovou_dentes', v)} />
                  <SelectBoolean label="Sinalizou banheiro?" checked={form.higiene.sinalizou_banheiro} onChange={v => updateSection('higiene', 'sinalizou_banheiro', v)} />
                </div>
              </div>
              {/* Vestuario */}
              <div>
                <h4 className="text-sm font-semibold mb-2">Vestuário</h4>
                <div className="grid grid-cols-2 gap-4">
                  <SelectBoolean label="Colaborou ao vestir?" checked={form.vestuario.colaborou_roupa} onChange={v => updateSection('vestuario', 'colaborou_roupa', v)} />
                  <SelectBoolean label="Incômodo sensorial (etiqueta/tecido)?" checked={form.vestuario.incomodo_sensorial} onChange={v => updateSection('vestuario', 'incomodo_sensorial', v)} />
                </div>
              </div>
              {/* Rotina */}
              <div>
                <h4 className="text-sm font-semibold mb-2">Rotina</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <SelectBoolean label="Guardou brinquedos?" checked={form.rotina.guardou_brinquedos} onChange={v => updateSection('rotina', 'guardou_brinquedos', v)} />
                  <SelectBoolean label="Ajudou tarefa?" checked={form.rotina.ajudou_tarefa} onChange={v => updateSection('rotina', 'ajudou_tarefa', v)} />
                  <SelectBoolean label="Aceitou transição?" checked={form.rotina.aceitou_transicao} onChange={v => updateSection('rotina', 'aceitou_transicao', v)} />
                  <SelectBoolean label="Foi para a escola?" checked={form.rotina.teve_escola} onChange={v => updateSection('rotina', 'teve_escola', v)} />
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
