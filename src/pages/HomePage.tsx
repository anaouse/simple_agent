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
  const activeMessageIdRef = useRef<string | null>(null)
  const messageCreatedAtRef = useRef(new Map<string, string>())

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
      activeMessageIdRef.current = event.messageId
      messageCreatedAtRef.current.set(event.messageId, event.createdAt)
      return
    }
    if (event.type === 'content_delta') {
      setMessages((current) => {
        const last = current.at(-1)
        if (
          last?.role === 'assistant'
          && (last.id === event.messageId || last.parentMessageId === event.messageId)
        ) {
          return current.map((item) =>
            item.id === last.id ? { ...item, content: item.content + event.delta } : item
          )
        }
        return [...current, {
          id: crypto.randomUUID(),
          parentMessageId: event.messageId,
          role: 'assistant',
          content: event.delta,
          status: 'streaming',
          createdAt: messageCreatedAtRef.current.get(event.messageId) ?? new Date().toISOString(),
        }]
      })
      return
    }
    if (event.type === 'tool_call_start') {
      setMessages((current) => [
        ...current.map((item) =>
          item.role === 'assistant'
            && item.parentMessageId === event.messageId
            && item.status === 'streaming'
            ? { ...item, status: 'complete' as const }
            : item
        ),
        {
          id: event.toolCallId,
          role: 'tool',
          parentMessageId: event.messageId,
          toolName: event.toolName,
          arguments: event.arguments,
          result: '',
          status: 'streaming',
          createdAt: messageCreatedAtRef.current.get(event.messageId) ?? new Date().toISOString(),
        },
      ])
      return
    }
    if (event.type === 'tool_call_result') {
      setMessages((current) => current.map((item) =>
        item.role === 'tool' && item.id === event.toolCallId
          ? { ...item, result: event.result, status: event.isError ? 'error' : 'complete' }
          : item
      ))
      return
    }
    if (event.type === 'message_end') {
      setMessages((current) => current.map((item) =>
        (item.id === event.messageId || item.parentMessageId === event.messageId)
          && item.status === 'streaming'
          ? { ...item, status: 'complete' }
          : item
      ))
      messageCreatedAtRef.current.delete(event.messageId)
      activeMessageIdRef.current = null
      setWaiting(false)
      return
    }
    setMessages((current) => {
      let foundActiveNode = false
      const updated = current.map((item) => {
        if (item.status !== 'streaming') return item
        foundActiveNode = true
        if (item.role === 'assistant') {
          return { ...item, content: item.content || event.error.message, status: 'error' as const }
        }
        if (item.role === 'tool') {
          return { ...item, result: item.result || event.error.message, status: 'error' as const }
        }
        return item
      })
      const messageId = activeMessageIdRef.current
      if (foundActiveNode || !messageId) return updated
      return [...updated, {
        id: messageId,
        role: 'assistant',
        content: event.error.message,
        status: 'error',
        createdAt: messageCreatedAtRef.current.get(messageId) ?? new Date().toISOString(),
      }]
    })
    if (activeMessageIdRef.current) {
      messageCreatedAtRef.current.delete(activeMessageIdRef.current)
      activeMessageIdRef.current = null
    }
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
