export interface Project {
  path: string
}

export interface ModelSummary {
  name: string
  compatible: string
}

export interface ModelListResponse {
  models: ModelSummary[]
}

export interface ModelsEvent {
  type: 'models'
  models: ModelSummary[]
}

export interface SkillEntry {
  name: string
}

export interface SkillsEvent {
  type: 'skills'
  entries: SkillEntry[]
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
  type: 'message'
  content: string
}

export interface ProjectFileEntry {
  path: string
  absolutePath: string
  isDirectory: boolean
}

export interface ProjectFilesEvent {
  type: 'project_files'
  entries: ProjectFileEntry[]
}

export interface SessionResponse {
  sessionFile: string | null
  messages: ChatMessage[]
}

export interface SessionSummary {
  fileName: string
}

export interface SessionListResponse {
  sessions: SessionSummary[]
}

export interface OpenSessionRequest {
  projectPath: string
  sessionFile: string
}

export interface NewSessionRequest {
  projectPath: string
}

export interface NewSessionResponse {
  projectPath: string
  sessionFile: string
}

export interface InterruptSessionRequest {
  projectPath: string
}

export interface InterruptSessionResponse {
  interrupted: boolean
}

export interface UserMessageEvent {
  type: 'user_message'
  content: string
  createdAt: string
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
  | UserMessageEvent
  | MessageStartEvent
  | ContentDeltaEvent
  | ToolCallStartEvent
  | ToolCallResultEvent
  | MessageEndEvent
  | ErrorEvent
