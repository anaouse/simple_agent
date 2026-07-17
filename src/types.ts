export type MessageRole = 'user' | 'assistant'
export type MessageStatus = 'complete' | 'streaming' | 'error'

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  status: MessageStatus
  createdAt: string
}

export interface ClientMessage {
  type: 'message'
  content: string
}

export interface MessageStartEvent {
  type: 'message_start'
  messageId: string
  createdAt: string
}

export interface ContentDeltaEvent {
  type: 'content_delta'
  messageId: string
  delta: string
}

export interface MessageEndEvent {
  type: 'message_end'
  messageId: string
}

export interface ErrorBody {
  code: string
  message: string
}

export interface ErrorEvent {
  type: 'error'
  error: ErrorBody
}

export type ServerEvent = MessageStartEvent | ContentDeltaEvent | MessageEndEvent | ErrorEvent
