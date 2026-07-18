import { ChangeEvent, FormEvent, KeyboardEvent, useEffect, useRef, useState } from 'react'
import type { ProjectFileEntry } from '@/types'

interface InputBoxProps {
  disabled: boolean
  files: ProjectFileEntry[]
  newSessionDisabled: boolean
  onNewSession: () => void
  onSend: (content: string) => void
}

interface AtQuery {
  start: number
  end: number
  query: string
}

const MAX_RESULTS = 30

export default function InputBox({ disabled, files, newSessionDisabled, onNewSession, onSend }: InputBoxProps) {
  const [content, setContent] = useState('')
  const [cursor, setCursor] = useState(0)
  const [activeIndex, setActiveIndex] = useState(0)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const activeSuggestionRef = useRef<HTMLButtonElement>(null)
  const atQuery = findAtQuery(content, cursor)
  const suggestions = atQuery ? filterFiles(files, atQuery.query) : []

  useEffect(() => {
    activeSuggestionRef.current?.scrollIntoView({ block: 'nearest' })
  }, [activeIndex])

  function send() {
    const value = content.trim()
    if (!value || disabled) return
    onSend(value)
    setContent('')
    setCursor(0)
    resetHeight()
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    send()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (suggestions.length > 0 && atQuery) {
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault()
        const direction = event.key === 'ArrowDown' ? 1 : -1
        setActiveIndex((current) => (current + direction + suggestions.length) % suggestions.length)
        return
      }
      if (event.key === 'Tab' || (event.key === 'Enter' && !event.shiftKey)) {
        event.preventDefault()
        selectSuggestion(suggestions[activeIndex] ?? suggestions[0], atQuery)
        return
      }
    }
    // Enter sends the message, Shift+Enter inserts a newline
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      send()
    }
  }

  function handleChange(event: ChangeEvent<HTMLTextAreaElement>) {
    setContent(event.target.value)
    setCursor(event.target.selectionStart)
    setActiveIndex(0)
    autoGrow(event.target)
  }

  function handleKeyUp(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (['ArrowUp', 'ArrowDown', 'Enter', 'Tab'].includes(event.key)) return
    syncCursor()
  }

  function selectSuggestion(entry: ProjectFileEntry, query: AtQuery) {
    const replacement = `@${entry.absolutePath} `
    const nextContent = content.slice(0, query.start) + replacement + content.slice(query.end)
    const nextCursor = query.start + replacement.length
    setContent(nextContent)
    setCursor(nextCursor)
    setActiveIndex(0)
    requestAnimationFrame(() => {
      const element = textareaRef.current
      if (!element) return
      element.focus()
      element.setSelectionRange(nextCursor, nextCursor)
      autoGrow(element)
    })
  }

  function syncCursor() {
    setCursor(textareaRef.current?.selectionStart ?? 0)
    setActiveIndex(0)
  }

  function autoGrow(element: HTMLTextAreaElement) {
    element.style.height = 'auto'
    element.style.height = `${element.scrollHeight}px`
  }

  function resetHeight() {
    const element = textareaRef.current
    if (element) element.style.height = 'auto'
  }

  return (
    <form className="input-box" onSubmit={submit}>
      <button
        className="input-box__new-session"
        disabled={newSessionDisabled}
        onClick={onNewSession}
        type="button"
      >
        新对话
      </button>
      <div className="input-box__editor">
        {suggestions.length > 0 && atQuery && (
          <div className="input-box__suggestions" role="listbox">
            {suggestions.map((entry, index) => (
              <button
                aria-selected={index === activeIndex}
                className={index === activeIndex ? 'input-box__suggestion input-box__suggestion--active' : 'input-box__suggestion'}
                key={entry.path}
                onMouseDown={(event) => event.preventDefault()}
                ref={index === activeIndex ? activeSuggestionRef : undefined}
                onClick={() => selectSuggestion(entry, atQuery)}
                role="option"
                type="button"
              >
                <span>{entry.isDirectory ? '📁' : '📄'}</span>
                <span>{entry.path}</span>
              </button>
            ))}
          </div>
        )}
        <textarea
          aria-label="消息"
          disabled={disabled}
          onChange={handleChange}
          onClick={syncCursor}
          onKeyDown={handleKeyDown}
          onKeyUp={handleKeyUp}
          placeholder="输入消息，使用 @ 引用项目文件…"
          ref={textareaRef}
          rows={1}
          value={content}
        />
      </div>
      <button disabled={disabled || !content.trim()} type="submit">
        发送
      </button>
    </form>
  )
}

function findAtQuery(content: string, cursor: number): AtQuery | null {
  const beforeCursor = content.slice(0, cursor)
  const start = beforeCursor.lastIndexOf('@')
  if (start < 0) return null
  const query = beforeCursor.slice(start + 1)
  if (/\s/.test(query)) return null
  return { start, end: cursor, query: query.toLowerCase() }
}

function filterFiles(files: ProjectFileEntry[], query: string): ProjectFileEntry[] {
  return files
    .filter((entry) => !query || entry.path.toLowerCase().includes(query))
    .sort((left, right) => {
      const leftPath = left.path.toLowerCase()
      const rightPath = right.path.toLowerCase()
      const leftScore = !query || leftPath === query ? 0 : leftPath.startsWith(query) ? 1 : 2
      const rightScore = !query || rightPath === query ? 0 : rightPath.startsWith(query) ? 1 : 2
      return leftScore - rightScore || left.path.length - right.path.length || leftPath.localeCompare(rightPath)
    })
    .slice(0, MAX_RESULTS)
}
