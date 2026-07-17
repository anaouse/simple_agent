import { FormEvent, useState } from 'react'

interface InputBoxProps {
  disabled: boolean
  onSend: (content: string) => void
}

export default function InputBox({ disabled, onSend }: InputBoxProps) {
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
