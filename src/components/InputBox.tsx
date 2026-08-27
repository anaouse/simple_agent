import { ChangeEvent, ClipboardEvent, forwardRef, FormEvent, KeyboardEvent, useEffect, useImperativeHandle, useRef, useState } from 'react'
import Attachments from '@/components/Attachments'
import type { Attachment, ModelSummary, ProjectFileEntry, SkillEntry } from '@/types'

interface InputBoxProps {
  disabled: boolean
  error: string | null
  files: ProjectFileEntry[]
  models: ModelSummary[]
  skills: SkillEntry[]
  newSessionDisabled: boolean
  waiting: boolean
  onModelSelect: (modelName: string) => void
  onNewSession: () => void
  onSend: (content: string, attachments: Attachment[]) => void
  onStop: () => void
}

interface TextQuery {
  start: number
  end: number
  query: string
}

interface Suggestion {
  key: string
  icon: string
  label: string
  onSelect: () => void
}

const MAX_RESULTS = 30

export interface InputBoxHandle {
  focus: () => boolean
  restore: (content: string, attachments: Attachment[]) => void
}

const InputBox = forwardRef<InputBoxHandle, InputBoxProps>(function InputBox({
  disabled,
  error,
  files,
  models,
  skills,
  newSessionDisabled,
  waiting,
  onModelSelect,
  onNewSession,
  onSend,
  onStop,
}, ref) {
  const [content, setContent] = useState('')
  const [cursor, setCursor] = useState(0)
  const [activeIndex, setActiveIndex] = useState(0)
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const activeSuggestionRef = useRef<HTMLButtonElement>(null)
  const atQuery = findAtQuery(content, cursor)
  const slashQuery = findSlashQuery(content, cursor)
  const modelQuery = findCommandQuery(content, cursor, 'model')
  const skillQuery = findCommandQuery(content, cursor, 'skill')
  const suggestions = buildSuggestions()

  useEffect(() => {
    activeSuggestionRef.current?.scrollIntoView({ block: 'nearest' })
  }, [activeIndex])

  useImperativeHandle(ref, () => ({
    focus() {
      if (disabled) return false
      requestAnimationFrame(() => textareaRef.current?.focus())
      return true
    },
    restore(nextContent: string, nextAttachments: Attachment[]) {
      setContent(nextContent)
      setAttachments(nextAttachments)
      setCursor(nextContent.length)
      setActiveIndex(0)
      requestAnimationFrame(() => {
        const element = textareaRef.current
        if (!element) return
        element.focus()
        element.setSelectionRange(nextContent.length, nextContent.length)
        autoGrow(element)
      })
    },
  }), [disabled])

  function buildSuggestions(): Suggestion[] {
    if (atQuery) {
      return filterFiles(files, atQuery.query).map((entry) => ({
        key: `file:${entry.absolutePath}`,
        icon: entry.isDirectory ? '📁' : '📄',
        label: entry.path,
        onSelect: () => replaceQuery(atQuery, `@${entry.absolutePath} `),
      }))
    }
    if (modelQuery) {
      return models
        .filter((model) => model.name.toLowerCase().includes(modelQuery.query))
        .slice(0, MAX_RESULTS)
        .map((model) => ({
          key: `model:${model.name}`,
          icon: '◆',
          label: model.name,
          onSelect: () => selectModel(model.name),
        }))
    }
    if (skillQuery) {
      return skills
        .filter((skill) => skill.name.toLowerCase().includes(skillQuery.query))
        .slice(0, MAX_RESULTS)
        .map((skill) => ({
          key: `skill:${skill.name}`,
          icon: '◆',
          label: skill.name,
          onSelect: () => replaceQuery(skillQuery, `/skill ${skill.name} `),
        }))
    }
    if (slashQuery) {
      return ['model', 'skill']
        .filter((command) => command.includes(slashQuery.query))
        .map((command) => ({
          key: `command:${command}`,
          icon: '',
          label: `/${command}`,
          onSelect: () => replaceQuery(slashQuery, `/${command} `),
        }))
    }
    return []
  }

  function send() {
    const value = content.trim()
    const hasAttachments = attachments.length > 0
    if ((!value && !hasAttachments) || disabled) return
    if (!hasAttachments) {
      if (value === '/model' || value === '/skill') return
      if (value.startsWith('/model ')) {
        const modelName = value.slice('/model '.length).trim()
        if (models.some((model) => model.name === modelName)) selectModel(modelName)
        return
      }
    }
    onSend(value, attachments)
    clearInput()
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    send()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (suggestions.length > 0) {
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault()
        const direction = event.key === 'ArrowDown' ? 1 : -1
        setActiveIndex((current) => (current + direction + suggestions.length) % suggestions.length)
        return
      }
      if (event.key === 'Tab' || (event.key === 'Enter' && !event.shiftKey)) {
        event.preventDefault()
        ;(suggestions[activeIndex] ?? suggestions[0]).onSelect()
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

  function handlePaste(event: ClipboardEvent<HTMLTextAreaElement>) {
    const files = Array.from(event.clipboardData?.items ?? [])
      .filter((item) => item.type.startsWith('image/'))
      .map((item) => item.getAsFile())
      .filter((file): file is File => file !== null)
    if (files.length === 0) return
    event.preventDefault()
    for (const file of files) {
      const reader = new FileReader()
      reader.onload = () => {
        const dataUrl = typeof reader.result === 'string' ? reader.result : ''
        const match = dataUrl.match(/^data:([^;]+);base64,(.*)$/)
        if (!match) return
        setAttachments((current) => [
          ...current,
          { mediaType: match[1], data: match[2] },
        ])
      }
      reader.readAsDataURL(file)
    }
  }

  function handleKeyUp(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (['ArrowUp', 'ArrowDown', 'Enter', 'Tab'].includes(event.key)) return
    syncCursor()
  }

  function replaceQuery(query: TextQuery, replacement: string) {
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

  function selectModel(modelName: string) {
    onModelSelect(modelName)
    clearInput()
  }

  function clearInput() {
    setContent('')
    setCursor(0)
    setActiveIndex(0)
    setAttachments([])
    resetHeight()
  }

  function syncCursor() {
    setCursor(textareaRef.current?.selectionStart ?? 0)
    setActiveIndex(0)
  }

  function autoGrow(element: HTMLTextAreaElement) {
    element.style.height = 'auto'
    const borderHeight = element.offsetHeight - element.clientHeight
    element.style.height = `${element.scrollHeight + borderHeight}px`
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
        {suggestions.length > 0 && (
          <div className="input-box__suggestions" role="listbox">
            {suggestions.map((suggestion, index) => (
              <button
                aria-selected={index === activeIndex}
                className={index === activeIndex ? 'input-box__suggestion input-box__suggestion--active' : 'input-box__suggestion'}
                key={suggestion.key}
                onMouseDown={(event) => event.preventDefault()}
                ref={index === activeIndex ? activeSuggestionRef : undefined}
                onClick={suggestion.onSelect}
                role="option"
                type="button"
              >
                <span>{suggestion.icon}</span>
                <span>{suggestion.label}</span>
              </button>
            ))}
          </div>
        )}
        {error && <div className="input-box__error">{error}</div>}
        {attachments.length > 0 && (
          <Attachments
            attachments={attachments}
            onRemove={(index) => setAttachments((current) => current.filter((_, i) => i !== index))}
          />
        )}
        <textarea
          aria-label="消息"
          disabled={disabled}
          onChange={handleChange}
          onClick={syncCursor}
          onKeyDown={handleKeyDown}
          onKeyUp={handleKeyUp}
          onPaste={handlePaste}
          placeholder="输入消息，使用 @ 引用文件或 / 执行命令…"
          ref={textareaRef}
          rows={1}
          value={content}
        />
      </div>
      {waiting ? (
        <button onClick={onStop} type="button">
          停止
        </button>
      ) : (
        <button disabled={disabled || (!content.trim() && attachments.length === 0)} type="submit">
          发送
        </button>
      )}
    </form>
  )
})

export default InputBox

function findAtQuery(content: string, cursor: number): TextQuery | null {
  const beforeCursor = content.slice(0, cursor)
  const start = beforeCursor.lastIndexOf('@')
  if (start < 0) return null
  const query = beforeCursor.slice(start + 1)
  if (/\s/.test(query)) return null
  return { start, end: cursor, query: query.toLowerCase() }
}

function findSlashQuery(content: string, cursor: number): TextQuery | null {
  const beforeCursor = content.slice(0, cursor)
  if (!beforeCursor.startsWith('/') || /\s/.test(beforeCursor)) return null
  return { start: 0, end: cursor, query: beforeCursor.slice(1).toLowerCase() }
}

function findCommandQuery(content: string, cursor: number, command: string): TextQuery | null {
  const beforeCursor = content.slice(0, cursor)
  const match = beforeCursor.match(new RegExp(`^/${command}\\s+(.*)$`, 'i'))
  if (!match) return null
  return { start: 0, end: cursor, query: match[1].trim().toLowerCase() }
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
