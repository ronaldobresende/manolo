'use client'

interface ToggleProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label?: string
}

export function Toggle({ checked, onChange, label }: ToggleProps) {
  return (
    <label className="flex items-center cursor-pointer select-none">
      <div className="relative">
        <input
          type="checkbox"
          className="sr-only"
          checked={checked || false}
          onChange={(e) => onChange(e.target.checked)}
        />
        <div
          className={`block w-10 h-6 rounded-full transition-colors ${
            checked ? 'bg-primary' : 'bg-neutral-border'
          }`}
        ></div>
        <div
          className={`absolute left-1 top-1 bg-white w-4 h-4 rounded-full transition-transform ${
            checked ? 'transform translate-x-4' : ''
          }`}
        ></div>
      </div>
      {label && <span className="ml-3 text-sm text-manolo-text">{label}</span>}
    </label>
  )
}
