import type { ChatMessage } from '@/types'

interface SessionInfoProps {
  modelName: string | null
  messages: ChatMessage[]
}

function messageCharacterCount(message: ChatMessage) {
  if (message.role !== 'tool') return message.content.length
  return message.toolName.length + JSON.stringify(message.arguments).length + message.result.length
}

export default function SessionInfo({ modelName, messages }: SessionInfoProps) {
  const characterCount = messages.reduce((total, message) => total + messageCharacterCount(message), 0)

  return (
    <div className="session-info">
      <span>当前模型</span>
      <strong>{modelName ?? '未加载'}</strong>
      <span>当前对话</span>
      <strong>{characterCount} 字符</strong>
    </div>
  )
}
