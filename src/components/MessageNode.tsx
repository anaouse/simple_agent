import { useState } from 'react'
import { Streamdown } from 'streamdown'
import { createMathPlugin } from '@streamdown/math'
import { code } from '@streamdown/code'
import type { ChatMessage } from '@/types'

interface MessageNodeProps {
  message: ChatMessage
}

const math = createMathPlugin({
  singleDollarTextMath: true, // 打开单 $ 识别
})

export default function MessageNode({ message }: MessageNodeProps) {
  const [expanded, setExpanded] = useState(false)
  const role = message.role === 'user' ? '你' : 'Agent'

  return (
    <article className={`message-node message-node--${message.role}`}>
      <button className="message-node__header" onClick={() => setExpanded(!expanded)} type="button">
        <span>{role}</span>
        <span className="message-node__meta">
          {message.status === 'streaming' ? '回应中' : expanded ? '收起' : '展开'}
        </span>
      </button>
      {expanded && (
        <div className="message-node__content">
          {message.role === 'assistant' ? (
            <Streamdown
              mode={message.status === 'streaming' ? 'streaming' : 'static'}
              plugins={{ math, code }}
            >
              {message.content || '…'}
            </Streamdown>
          ) : (
            <p>{message.content}</p>
          )}
          {message.status === 'error' && <p className="message-node__error">生成失败</p>}
        </div>
      )}
    </article>
  )
}
