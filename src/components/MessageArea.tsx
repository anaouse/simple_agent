import type { KeyboardEvent } from 'react'
import MessageNode from '@/components/MessageNode'
import type { ChatMessage } from '@/types'

interface MessageAreaProps {
  messages: ChatMessage[]
  onSlash: () => boolean
}

export default function MessageArea({ messages, onSlash }: MessageAreaProps) {
  function handleKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (event.key === '/' && !event.ctrlKey && !event.altKey && !event.metaKey && onSlash()) {
      event.preventDefault()
    }
  }

  return (
    <main className="message-area" onKeyDown={handleKeyDown} tabIndex={0}>
      {messages.length === 0 && <p className="message-area__empty">发送一条消息开始聊天</p>}
      {messages.map((message) => <MessageNode key={message.id} message={message} />)}
    </main>
  )
}
