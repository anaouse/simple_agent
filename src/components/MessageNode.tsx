import { useEffect, useRef, useState } from 'react'
import { Streamdown } from 'streamdown'
import { createMathPlugin } from '@streamdown/math'
import { code } from '@streamdown/code'
import Attachments from '@/components/Attachments'
import type { ChatMessage } from '@/types'

interface MessageNodeProps {
  message: ChatMessage
  expandSignal: string | null
}

const math = createMathPlugin({
  singleDollarTextMath: true, // Enable single-dollar math syntax
})

function statusText(message: ChatMessage, expanded: boolean) {
  if (message.status === 'streaming') {
    return message.role === 'tool' ? '执行中' : '回应中'
  }
  if (message.status === 'error') return '失败'
  return expanded ? '收起' : '展开'
}

function messagePreview(message: ChatMessage) {
  if (message.role === 'tool') {
    const content = message.result || JSON.stringify(message.arguments)
    const normalized = content.replace(/\s+/g, ' ').trim()
    return normalized.length > 80 ? `${normalized.slice(0, 80)}…` : normalized
  }
  const parts: string[] = []
  const text = message.content.replace(/\s+/g, ' ').trim()
  if (text) parts.push(text)
  if (message.role === 'user' && message.attachments?.length) {
    parts.push(`[${message.attachments.length} 张图片]`)
  }
  const label = parts.join(' ')
  return label.length > 80 ? `${label.slice(0, 80)}…` : label
}

function copyContent(message: ChatMessage) {
  return message.role === 'tool' ? JSON.stringify(message, null, 2) : message.content
}

export default function MessageNode({ message, expandSignal }: MessageNodeProps) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)
  const copyTimer = useRef<number | undefined>(undefined)
  const previousExpandSignalRef = useRef(expandSignal)

  useEffect(() => () => window.clearTimeout(copyTimer.current), [])

  useEffect(() => {
    if (expandSignal && expandSignal !== previousExpandSignalRef.current) setExpanded(true)
    previousExpandSignalRef.current = expandSignal
  }, [expandSignal])

  async function handleCopy() {
    await navigator.clipboard.writeText(copyContent(message))
    window.clearTimeout(copyTimer.current)
    setCopied(true)
    copyTimer.current = window.setTimeout(() => setCopied(false), 3000)
  }

  return (
    <article className={`message-node message-node--${message.role}${expanded ? ' message-node--expanded' : ''}`}>
      <div className="message-node__header">
        <button className="message-node__header-toggle" onClick={() => setExpanded(!expanded)} type="button">
          {message.role === 'tool' && <span className="message-node__title">{message.toolName}</span>}
          {!expanded && <span className="message-node__preview">{messagePreview(message)}</span>}
          <span className="message-node__meta">{statusText(message, expanded)}</span>
        </button>
        <button
          className="message-node__copy"
          onClick={() => void handleCopy()}
          type="button"
        >
          {copied ? '✓ 已复制' : '复制'}
        </button>
      </div>
      {expanded && (
        <div className="message-node__content">
          {message.role === 'tool' ? (
            <div className="message-node__tool-details">
              <section>
                <strong>参数</strong>
                <pre>{JSON.stringify(message.arguments, null, 2)}</pre>
              </section>
              <section>
                <strong>结果</strong>
                <pre className={message.status === 'error' ? 'message-node__tool-result--error' : undefined}>
                  {message.result || '执行中…'}
                </pre>
              </section>
            </div>
          ) : message.role === 'assistant' ? (
            <Streamdown
              mode={message.status === 'streaming' ? 'streaming' : 'static'}
              plugins={{ math, code }}
            >
              {message.content || '…'}
            </Streamdown>
          ) : (
            <>
              {message.content && <p>{message.content}</p>}
              {message.attachments && message.attachments.length > 0 && (
                <Attachments attachments={message.attachments} />
              )}
            </>
          )}
          {message.role !== 'tool' && message.status === 'error' && (
            <p className="message-node__error">生成失败</p>
          )}
        </div>
      )}
    </article>
  )
}
