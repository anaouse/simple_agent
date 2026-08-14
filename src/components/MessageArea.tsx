import { useEffect, useRef } from 'react'
import MessageNode from '@/components/MessageNode'
import type { ChatMessage } from '@/types'

interface MessageAreaProps {
  messages: ChatMessage[]
  toolsHidden: boolean
  completedMessageId: string | null
}

export default function MessageArea({ messages, toolsHidden, completedMessageId }: MessageAreaProps) {
  const areaRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    function handleWheel(event: WheelEvent) {
      const target = event.target
      if (!(target instanceof Element) || !areaRef.current) return
      // 消息区内部、sidebar 内部保持原生滚动（含工具结果 pre、sidebar 列表等嵌套滚动）
      if (target.closest('.message-area') || target.closest('.project-sidebar')) return
      event.preventDefault()
      areaRef.current.scrollTop += event.deltaY
    }
    window.addEventListener('wheel', handleWheel, { capture: true, passive: false })
    return () => window.removeEventListener('wheel', handleWheel, { capture: true })
  }, [])

  const visibleMessages = toolsHidden ? messages.filter((message) => message.role !== 'tool') : messages
  const lastCompletedMessage = completedMessageId
    ? visibleMessages.findLast((message) => message.id === completedMessageId || message.parentMessageId === completedMessageId)
    : undefined

  return (
    <main className="message-area" ref={areaRef}>
      {visibleMessages.length === 0 && <p className="message-area__empty">发送一条消息开始聊天</p>}
      {visibleMessages.map((message) => (
        <MessageNode
          key={message.id}
          message={message}
          expandSignal={message.id === lastCompletedMessage?.id ? completedMessageId : null}
        />
      ))}
    </main>
  )
}
