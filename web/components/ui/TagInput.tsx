'use client'

import { useState } from 'react'

interface TagInputProps {
  tags: string[]
  onChange: (tags: string[]) => void
  placeholder?: string
}

export function TagInput({ tags = [], onChange, placeholder = 'Adicionar...' }: TagInputProps) {
  const [input, setInput] = useState('')

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      const val = input.trim()
      if (val && !tags.includes(val)) {
        onChange([...tags, val])
        setInput('')
      }
    } else if (e.key === 'Backspace' && !input && tags.length > 0) {
      onChange(tags.slice(0, -1))
    }
  }

  const removeTag = (index: number) => {
    const newTags = [...tags]
    newTags.splice(index, 1)
    onChange(newTags)
  }

  return (
    <div className="flex flex-wrap gap-2 p-2 border border-neutral-border rounded-lg bg-white focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition-all">
      {tags.map((tag, i) => (
        <span 
          key={i} 
          className="flex items-center gap-1 px-2 py-1 bg-primary/10 text-primary-dark text-sm rounded-md"
        >
          {tag}
          <button
            type="button"
            onClick={() => removeTag(i)}
            className="text-primary hover:text-primary-dark w-4 h-4 flex items-center justify-center rounded-full hover:bg-primary/20 transition-colors"
          >
            ×
          </button>
        </span>
      ))}
      <input
        type="text"
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={tags.length === 0 ? placeholder : ''}
        className="flex-1 min-w-[120px] outline-none text-sm text-manolo-text placeholder:text-manolo-muted bg-transparent p-1"
      />
    </div>
  )
}
