import React, { useState, useRef, FormEvent } from 'react'
import { SendIcon } from '@heroicons/react/24/outline'

interface MessageInputProps {
  value: string
  onChange: (value: string) => void
  onSend: (message: string) => void
  disabled?: boolean
  placeholder?: string
}

export function MessageInput({
  value,
  onChange,
  onSend,
  disabled = false,
  placeholder = "Type your message..."
}: MessageInputProps) {
  const [isComposing, setIsComposing] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (value.trim() && !disabled && !isComposing) {
      onSend(value.trim())
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  // Auto-resize textarea
  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value)

    // Auto-resize
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }
  }

  return (
    <form onSubmit={handleSubmit} className="relative">
      <div className="flex items-end space-x-3">
        <div className="flex-1">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            onCompositionStart={() => setIsComposing(true)}
            onCompositionEnd={() => setIsComposing(false)}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className={clsx(
              'block w-full resize-none border-0 rounded-lg bg-gray-100 dark:bg-gray-700',
              'placeholder-gray-500 dark:placeholder-gray-400',
              'focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900',
              'text-sm text-gray-900 dark:text-white',
              disabled && 'opacity-50 cursor-not-allowed',
              'px-4 py-3 pr-12 scrollbar-thin'
            )}
            style={{
              minHeight: '48px',
              maxHeight: '200px',
            }}
          />
        </div>

        <div className="flex-shrink-0">
          <button
            type="submit"
            disabled={!value.trim() || disabled}
            className={clsx(
              'inline-flex items-center justify-center w-10 h-10 rounded-lg',
              'focus:outline-none focus:ring-2 focus:ring-offset-2',
              disabled:opacity-50 disabled:cursor-not-allowed',
              value.trim() && !disabled
                ? 'bg-primary-600 hover:bg-primary-700 text-white focus:ring-primary-500'
                : 'bg-gray-200 dark:bg-gray-600 text-gray-400 dark:text-gray-300 focus:ring-gray-500'
            )}
          >
            <SendIcon className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="mt-2 flex items-center justify-between">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Press Enter to send, Shift+Enter for new line
        </p>
        {value.length > 500 && (
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {value.length} characters
          </p>
        )}
      </div>
    </form>
  )
}

function clsx(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ')
}