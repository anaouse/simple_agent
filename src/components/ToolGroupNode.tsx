import { useEffect, useRef, useState } from 'react'
import MessageNode from '@/components/MessageNode'
import type { ChatMessage } from '@/types'

interface ToolGroupNodeProps {
  messages: ChatMessage[]
  expandSignal: string | null
}

export default function ToolGroupNode({ messages, expandSignal }: ToolGroupNodeProps) {
  const [expanded, setExpanded] = useState(false)
  const previousExpandSignalRef = useRef(expandSignal)

  useEffect(() => {
    if (expandSignal && expandSignal !== previousExpandSignalRef.current) setExpanded(true)
    previousExpandSignalRef.current = expandSignal
  }, [expandSignal])

  const toolNames = messages.map((message) => message.toolName).join('、')
  const running = messages.some((message) => message.status === 'streaming')
  const failed = messages.some((message) => message.status === 'error')
  const statusText = running ? '多工具运行中' : failed ? '失败' : expanded ? '收起' : '展开'

  return (
    <section className={`tool-group${expanded ? ' tool-group--expanded' : ''}`}>
      <div className="tool-group__header">
        <button className="tool-group__toggle" onClick={() => setExpanded(!expanded)} type="button">
          <span className="tool-group__title">工具调用</span>
          <span className="tool-group__count">{messages.length}</span>
          {!expanded && <span className="tool-group__preview">{toolNames}</span>}
          <span className="tool-group__meta">{statusText}</span>
        </button>
      </div>
      {expanded && (
        <div className="tool-group__body">
          {messages.map((message, index) => (
            <MessageNode
              key={message.id}
              message={message}
              expandSignal={index === messages.length - 1 ? expandSignal : null}
            />
          ))}
        </div>
      )}
    </section>
  )
}
