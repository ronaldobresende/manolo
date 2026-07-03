import React from 'react'

interface SelectBooleanProps {
  label: string
  checked: boolean | null | undefined
  onChange: (value: boolean | null) => void
  className?: string
}

export function SelectBoolean({ label, checked, onChange, className = '' }: SelectBooleanProps) {
  // checked pode ser: true, false, ou null/undefined
  let selectValue = ''
  if (checked === true) selectValue = 'sim'
  else if (checked === false) selectValue = 'nao'

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value
    if (val === 'sim') onChange(true)
    else if (val === 'nao') onChange(false)
    else onChange(null)
  }

  return (
    <div className={`flex flex-col ${className}`}>
      <label className="text-sm font-medium text-manolo-text mb-1">{label}</label>
      <select 
        className="input bg-white" 
        value={selectValue} 
        onChange={handleChange}
      >
        <option value="">Não informado</option>
        <option value="sim">Sim</option>
        <option value="nao">Não</option>
      </select>
    </div>
  )
}
