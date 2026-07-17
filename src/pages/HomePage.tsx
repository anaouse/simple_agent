import { useEffect, useRef, useState } from 'react'
import InputBox from '@/components/InputBox'
import MessageArea from '@/components/MessageArea'
import type { ChatMessage, ClientMessage, ServerEvent } from '@/types'

const WS_URL = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.hostname}:2453/ws/chat`

export default function HomePage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [connected, setConnected] = useState(false)
  const [waiting, setWaiting] = useState(false)
  const socketRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const socket = new WebSocket(WS_URL)
    socketRef.current = socket
    socket.onopen = () => setConnected(true)
    socket.onclose = () => {
      setConnected(false)
      setWaiting(false)
    }
    socket.onmessage = (message) => handleEvent(JSON.parse(message.data) as ServerEvent)

    return () => socket.close()
  }, [])

  function handleEvent(event: ServerEvent) {
    if (event.type === 'message_start') {
      setMessages((current) => [...current, {
        id: event.messageId,
        role: 'assistant',
        content: '',
        status: 'streaming',
        createdAt: event.createdAt,
      }])
      return
    }
    if (event.type === 'content_delta') {
      setMessages((current) => current.map((item) =>
        item.id === event.messageId ? { ...item, content: item.content + event.delta } : item
      ))
      return
    }
    if (event.type === 'message_end') {
      setMessages((current) => current.map((item) =>
        item.id === event.messageId ? { ...item, status: 'complete' } : item
      ))
      setWaiting(false)
      return
    }
    setMessages((current) => current.map((item) =>
      item.status === 'streaming'
        ? { ...item, content: item.content || event.error.message, status: 'error' }
        : item
    ))
    setWaiting(false)
  }

  function send(content: string) {
    const socket = socketRef.current
    if (!socket || socket.readyState !== WebSocket.OPEN) return
    const message: ClientMessage = { type: 'message', content }
    setMessages((current) => [...current, {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      status: 'complete',
      createdAt: new Date().toISOString(),
    }])
    setWaiting(true)
    socket.send(JSON.stringify(message))
  }

  return (
    <div className="home-page">
      <header className="home-page__header">
        <strong>Agent</strong>
        <span>{connected ? '已连接' : '连接中…'}</span>
      </header>
      <MessageArea messages={messages} />
      <InputBox disabled={!connected || waiting} onSend={send} />
    </div>
  )
}
