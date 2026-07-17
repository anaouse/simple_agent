export interface Project {
  path: string
}

export interface ApiErrorResponse {
  error: ErrorBody
}

export type MessageRole = 'user' | 'assistant' | 'tool'
export type MessageStatus = 'complete' | 'streaming' | 'error'

interface BaseChatMessage {
  id: string
  status: MessageStatus
  createdAt: string
}

export interface TextChatMessage extends BaseChatMessage {
  role: 'user' | 'assistant'
  content: string
  parentMessageId?: string
}

export interface ToolChatMessage extends BaseChatMessage {
  role: 'tool'
  parentMessageId: string
  toolName: string
  arguments: Record<string, unknown>
  result: string
}

export type ChatMessage = TextChatMessage | ToolChatMessage

export interface ClientMessage {
  type: 'message' | 'project_switch'
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

export interface ToolCallStartEvent {
  type: 'tool_call_start'
  messageId: string
  toolCallId: string
  toolName: string
  arguments: Record<string, unknown>
}

export interface ToolCallResultEvent {
  type: 'tool_call_result'
  messageId: string
  toolCallId: string
  result: string
  isError: boolean
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

export type ServerEvent =
  | MessageStartEvent
  | ContentDeltaEvent
  | ToolCallStartEvent
  | ToolCallResultEvent
  | MessageEndEvent
  | ErrorEvent
