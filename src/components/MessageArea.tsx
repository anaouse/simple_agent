import MessageNode from '@/components/MessageNode'
import type { ChatMessage } from '@/types'

interface MessageAreaProps {
  messages: ChatMessage[]
  toolsHidden: boolean
}

export default function MessageArea({ messages, toolsHidden }: MessageAreaProps) {
  const visibleMessages = toolsHidden ? messages.filter((message) => message.role !== 'tool') : messages

  return (
    <main className="message-area">
      {visibleMessages.length === 0 && <p className="message-area__empty">发送一条消息开始聊天</p>}
      {visibleMessages.map((message) => <MessageNode key={message.id} message={message} />)}
    </main>
  )
}
