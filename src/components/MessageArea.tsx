import MessageNode from '@/components/MessageNode'
import type { ChatMessage } from '@/types'

interface MessageAreaProps {
  messages: ChatMessage[]
}

export default function MessageArea({ messages }: MessageAreaProps) {
  return (
    <main className="message-area">
      {messages.length === 0 && <p className="message-area__empty">发送一条消息开始聊天</p>}
      {messages.map((message) => <MessageNode key={message.id} message={message} />)}
    </main>
  )
}
