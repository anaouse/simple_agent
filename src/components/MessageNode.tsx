import { useState } from 'react'
import { Streamdown } from 'streamdown'
import { createMathPlugin } from '@streamdown/math'
import { code } from '@streamdown/code'
import type { ChatMessage } from '@/types'

interface MessageNodeProps {
  message: ChatMessage
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
  const content = message.role === 'tool'
    ? message.result || JSON.stringify(message.arguments)
    : message.content
  const normalized = content.replace(/\s+/g, ' ').trim()
  return normalized.length > 80 ? `${normalized.slice(0, 80)}…` : normalized
}

export default function MessageNode({ message }: MessageNodeProps) {
  const [expanded, setExpanded] = useState(false)
  const title = message.role === 'user'
    ? '你'
    : message.role === 'assistant'
      ? 'Agent'
      : `工具 · ${message.toolName}`

  return (
    <article className={`message-node message-node--${message.role}${expanded ? ' message-node--expanded' : ''}`}>
      <button className="message-node__header" onClick={() => setExpanded(!expanded)} type="button">
        <span className="message-node__title">{title}</span>
        {!expanded && <span className="message-node__preview">{messagePreview(message)}</span>}
        <span className="message-node__meta">{statusText(message, expanded)}</span>
      </button>
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
            <p>{message.content}</p>
          )}
          {message.role !== 'tool' && message.status === 'error' && (
            <p className="message-node__error">生成失败</p>
          )}
        </div>
      )}
    </article>
  )
}
