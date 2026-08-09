import MessageNode from '@/components/MessageNode'
import type { ChatMessage } from '@/types'

interface MessageAreaProps {
  messages: ChatMessage[]
  toolsHidden: boolean
  completedMessageId: string | null
}

export default function MessageArea({ messages, toolsHidden, completedMessageId }: MessageAreaProps) {
  const visibleMessages = toolsHidden ? messages.filter((message) => message.role !== 'tool') : messages
  const lastCompletedMessage = completedMessageId
    ? visibleMessages.findLast((message) => message.id === completedMessageId || message.parentMessageId === completedMessageId)
    : undefined

  return (
    <main className="message-area">
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
