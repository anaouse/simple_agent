import { FormEvent, useState } from 'react'

interface InputBoxProps {
  disabled: boolean
  newSessionDisabled: boolean
  onNewSession: () => void
  onSend: (content: string) => void
}

export default function InputBox({ disabled, newSessionDisabled, onNewSession, onSend }: InputBoxProps) {
  const [content, setContent] = useState('')

  function submit(event: FormEvent) {
    event.preventDefault()
    const value = content.trim()
    if (!value || disabled) return
    onSend(value)
    setContent('')
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
      <input
        aria-label="消息"
        disabled={disabled}
        onChange={(event) => setContent(event.target.value)}
        placeholder="输入消息…"
        value={content}
      />
      <button disabled={disabled || !content.trim()} type="submit">
        发送
      </button>
    </form>
  )
}
