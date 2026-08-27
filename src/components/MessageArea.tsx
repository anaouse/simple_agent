import { useEffect, useRef } from 'react'
import MessageNode from '@/components/MessageNode'
import ToolGroupNode from '@/components/ToolGroupNode'
import type { ChatMessage } from '@/types'

interface MessageAreaProps {
  messages: ChatMessage[]
  toolsHidden: boolean
  completedMessageId: string | null
}

type Row =
  | { type: 'message'; message: ChatMessage }
  | { type: 'group'; messages: ChatMessage[] }

export default function MessageArea({ messages, toolsHidden, completedMessageId }: MessageAreaProps) {
  const areaRef = useRef<HTMLElement | null>(null)
  const scrollTargetRef = useRef(0)
  const scrollAnimatingRef = useRef(false)
  const scrollRafRef = useRef(0)

  useEffect(() => {
    function smoothTick() {
      const el = areaRef.current
      if (!el) {
        scrollAnimatingRef.current = false
        return
      }
      const diff = scrollTargetRef.current - el.scrollTop
      if (Math.abs(diff) < 0.5) {
        el.scrollTop = scrollTargetRef.current
        scrollAnimatingRef.current = false
        return
      }
      // 每帧向目标值靠近 25%，形成类似原生滚动的平滑缓动
      el.scrollTop += diff * 0.25
      scrollRafRef.current = requestAnimationFrame(smoothTick)
    }

    function handleWheel(event: WheelEvent) {
      const target = event.target
      const el = areaRef.current
      if (!(target instanceof Element) || !el) return
      // 消息区内部、sidebar 内部保持原生滚动（含工具结果 pre、sidebar 列表等嵌套滚动）
      if (target.closest('.message-area') || target.closest('.project-sidebar')) {
        // 原生滚动期间同步目标值并停掉平滑动画，避免两者互相拉扯
        scrollTargetRef.current = el.scrollTop
        if (scrollAnimatingRef.current) {
          cancelAnimationFrame(scrollRafRef.current)
          scrollAnimatingRef.current = false
        }
        return
      }
      event.preventDefault()
      if (event.deltaY === 0) return
      // 新一次外部滚动开始时，以当前实际位置作为起点，避免把原生滚动后的位置覆盖掉
      if (!scrollAnimatingRef.current) scrollTargetRef.current = el.scrollTop
      scrollTargetRef.current += event.deltaY
      const maxScroll = el.scrollHeight - el.clientHeight
      scrollTargetRef.current = Math.max(0, Math.min(maxScroll, scrollTargetRef.current))
      if (!scrollAnimatingRef.current) {
        scrollAnimatingRef.current = true
        scrollRafRef.current = requestAnimationFrame(smoothTick)
      }
    }

    window.addEventListener('wheel', handleWheel, { capture: true, passive: false })
    return () => {
      window.removeEventListener('wheel', handleWheel, { capture: true })
      cancelAnimationFrame(scrollRafRef.current)
    }
  }, [])

  const visibleMessages = toolsHidden ? messages.filter((message) => message.role !== 'tool') : messages

  const rows: Row[] = []
  for (const message of visibleMessages) {
    if (message.role === 'tool') {
      const last = rows[rows.length - 1]
      if (last?.type === 'group') {
        last.messages.push(message)
      } else {
        rows.push({ type: 'group', messages: [message] })
      }
    } else {
      rows.push({ type: 'message', message })
    }
  }

  const lastCompletedMessage = completedMessageId
    ? visibleMessages.findLast((message) => message.id === completedMessageId || message.parentMessageId === completedMessageId)
    : undefined

  return (
    <main className="message-area" ref={areaRef}>
      {visibleMessages.length === 0 && <p className="message-area__empty">发送一条消息开始聊天</p>}
      {rows.map((row) => row.type === 'message' ? (
        <MessageNode
          key={row.message.id}
          message={row.message}
          expandSignal={row.message.id === lastCompletedMessage?.id ? completedMessageId : null}
        />
      ) : (
        <ToolGroupNode
          key={row.messages[0].id}
          messages={row.messages}
          expandSignal={row.messages.some((message) => message.id === lastCompletedMessage?.id) ? completedMessageId : null}
        />
      ))}
    </main>
  )
}
