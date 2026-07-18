import { ChangeEvent, FormEvent, KeyboardEvent, useRef, useState } from 'react'

interface InputBoxProps {
  disabled: boolean
  newSessionDisabled: boolean
  onNewSession: () => void
  onSend: (content: string) => void
}

export default function InputBox({ disabled, newSessionDisabled, onNewSession, onSend }: InputBoxProps) {
  const [content, setContent] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function send() {
    const value = content.trim()
    if (!value || disabled) return
    onSend(value)
    setContent('')
    resetHeight()
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    send()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends the message, Shift+Enter inserts a newline
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      send()
    }
  }

  function handleChange(event: ChangeEvent<HTMLTextAreaElement>) {
    setContent(event.target.value)
    autoGrow(event.target)
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
      <textarea
        aria-label="消息"
        disabled={disabled}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder="输入消息…"
        ref={textareaRef}
        rows={1}
        value={content}
      />
      <button disabled={disabled || !content.trim()} type="submit">
        发送
      </button>
    </form>
  )
}
