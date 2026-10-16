import axios from 'axios'
import { useEffect, useRef, useState } from 'react'
import InputBox, { type InputBoxHandle } from '@/components/InputBox'
import MessageArea from '@/components/MessageArea'
import ProjectSidebar from '@/components/ProjectSidebar'
import SessionInfo from '@/components/SessionInfo'
import type {
  Attachment,
  ApiErrorResponse,
  ChatMessage,
  ClientMessage,
  ModelSummary,
  InterruptSessionRequest,
  ModelsEvent,
  NewSessionRequest,
  NewSessionResponse,
  OpenSessionRequest,
  Project,
  ProjectFileEntry,
  ProjectFilesEvent,
  ServerEvent,
  SkillEntry,
  SkillsEvent,
  SessionResponse,
} from '@/types'

const BACKEND_PORT = import.meta.env.VITE_BACKEND_PORT || '2453'
const API_BASE_URL = `${location.protocol}//${location.hostname}:${BACKEND_PORT}/api`
const WS_BASE_URL = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.hostname}:${BACKEND_PORT}/ws/chat`
const FILES_WS_BASE_URL = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.hostname}:${BACKEND_PORT}/ws/project-files`
const MODELS_WS_BASE_URL = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.hostname}:${BACKEND_PORT}/ws/models`
const SKILLS_WS_BASE_URL = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.hostname}:${BACKEND_PORT}/ws/skills`
const PROJECTS_STORAGE_KEY = 'agent-projects'
const TOOLS_HIDDEN_STORAGE_KEY = 'agent-tools-hidden'

function loadProjects(): Project[] {
  try {
    const stored = JSON.parse(localStorage.getItem(PROJECTS_STORAGE_KEY) ?? '[]')
    if (!Array.isArray(stored)) return []
    return stored.filter((project): project is Project => (
      typeof project === 'object' && project !== null && typeof project.path === 'string'
    ))
  } catch {
    return []
  }
}

function loadToolsHidden(): boolean {
  return localStorage.getItem(TOOLS_HIDDEN_STORAGE_KEY) === 'true'
}

export default function HomePage() {
  const [projects, setProjects] = useState<Project[]>(loadProjects)
  const [activePath, setActivePath] = useState<string | null>(null)
  const [activeSessionFile, setActiveSessionFile] = useState<string | null>(null)
  const [sessionRefreshVersion, setSessionRefreshVersion] = useState(0)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [toolsHidden, setToolsHidden] = useState(loadToolsHidden)
  const [totalToken, setTotalToken] = useState(0)
  const [models, setModels] = useState<ModelSummary[]>([])
  const [skills, setSkills] = useState<SkillEntry[]>([])
  const [activeModelName, setActiveModelName] = useState<string | null>(null)
  const [projectFiles, setProjectFiles] = useState<ProjectFileEntry[]>([])
  const [connected, setConnected] = useState(false)
  const [waiting, setWaiting] = useState(false)
  const [inputError, setInputError] = useState<string | null>(null)
  const [completedMessageId, setCompletedMessageId] = useState<string | null>(null)
  const [startingSession, setStartingSession] = useState(false)
  const socketRef = useRef<WebSocket | null>(null)
  const inputBoxRef = useRef<InputBoxHandle | null>(null)
  const activeMessageIdRef = useRef<string | null>(null)
  const messageCreatedAtRef = useRef(new Map<string, string>())

  useEffect(() => {
    const socket = new WebSocket(MODELS_WS_BASE_URL)
    socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as ModelsEvent
      if (event.type !== 'models') return
      setModels(event.models)
      setActiveModelName((current) => event.defaultModel && event.models.some((model) => model.name === event.defaultModel)
        ? event.defaultModel
        : event.models[0]?.name ?? null)
    }
    socket.onclose = () => {
      setModels([])
      setActiveModelName(null)
    }
    return () => socket.close()
  }, [])

  useEffect(() => {
    const socket = new WebSocket(SKILLS_WS_BASE_URL)
    socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as SkillsEvent
      if (event.type === 'skills') setSkills(event.entries)
    }
    socket.onclose = () => setSkills([])
    return () => socket.close()
  }, [])

  useEffect(() => {
    localStorage.setItem(PROJECTS_STORAGE_KEY, JSON.stringify(projects))
  }, [projects])

  useEffect(() => {
    localStorage.setItem(TOOLS_HIDDEN_STORAGE_KEY, String(toolsHidden))
  }, [toolsHidden])

  useEffect(() => {
    function handleGlobalKeyDown(event: KeyboardEvent) {
      if (event.ctrlKey && event.key === '\\') {
        event.preventDefault()
        setSidebarCollapsed((current) => !current)
        return
      }
      if (
        event.key !== '/'
        || event.ctrlKey
        || event.altKey
        || event.metaKey
        || event.isComposing
      ) return
      const activeTag = (event.target as HTMLElement)?.tagName
      if (activeTag === 'INPUT' || activeTag === 'TEXTAREA') return
      if (inputBoxRef.current?.focus()) event.preventDefault()
    }
    document.addEventListener('keydown', handleGlobalKeyDown)
    return () => document.removeEventListener('keydown', handleGlobalKeyDown)
  }, [])

  useEffect(() => {
    return () => {
      socketRef.current?.close()
    }
  }, [])

  useEffect(() => {
    if (!activePath) {
      setProjectFiles([])
      return
    }
    const query = new URLSearchParams({ project_path: activePath })
    const socket = new WebSocket(`${FILES_WS_BASE_URL}?${query.toString()}`)
    socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as ProjectFilesEvent
      if (event.type === 'project_files') setProjectFiles(event.entries)
    }
    socket.onclose = () => setProjectFiles([])
    return () => socket.close()
  }, [activePath])

  function connect(path: string, sessionFile?: string | null, modelName = activeModelName) {
    socketRef.current?.close()
    setConnected(false)
    setWaiting(false)
    const query = new URLSearchParams({ project_path: path })
    if (sessionFile) query.set('session_file', sessionFile)
    if (modelName) query.set('model', modelName)
    const socket = new WebSocket(`${WS_BASE_URL}?${query.toString()}`)
    socketRef.current = socket
    socket.onopen = () => {
      if (socketRef.current !== socket) return
      setConnected(true)
    }
    socket.onclose = () => {
      if (socketRef.current !== socket) return
      setConnected(false)
      setWaiting(false)
    }
    socket.onmessage = (message) => {
      if (socketRef.current === socket) handleEvent(JSON.parse(message.data) as ServerEvent)
    }
  }

  async function selectProject(path: string) {
    if (path === activePath) return
    const currentSocket = socketRef.current
    if (currentSocket && currentSocket.readyState !== WebSocket.CLOSED) {
      await new Promise<void>((resolve) => {
        currentSocket.addEventListener('close', () => resolve(), { once: true })
        currentSocket.close()
      })
    }
    setMessages([])
    setTotalToken(0)
    activeMessageIdRef.current = null
    messageCreatedAtRef.current.clear()
    setActivePath(path)
    let sessionFile: string | null = null
    try {
      const request: NewSessionRequest = { projectPath: path }
      const response = await axios.post<NewSessionResponse>(`${API_BASE_URL}/sessions`, request)
      sessionFile = response.data.sessionFile
      setActiveSessionFile(sessionFile)
      setSessionRefreshVersion((current) => current + 1)
    } catch {
      setActiveSessionFile(null)
    }
    connect(path, sessionFile)
  }

  async function selectSession(path: string, fileName: string) {
    if (path === activePath && fileName === activeSessionFile) return
    const request: OpenSessionRequest = { projectPath: path, sessionFile: fileName }
    const response = await axios.post<SessionResponse>(`${API_BASE_URL}/sessions/open`, request)
    socketRef.current?.close()
    setActivePath(path)
    setActiveSessionFile(response.data.sessionFile)
    setMessages(response.data.messages)
    setTotalToken(response.data.totalToken)
    setCompletedMessageId(null)
    setWaiting(false)
    activeMessageIdRef.current = null
    messageCreatedAtRef.current.clear()
    connect(path, response.data.sessionFile)
  }

  function addProject(project: Project) {
    setProjects((current) => (
      current.some((item) => item.path === project.path) ? current : [...current, project]
    ))
  }

  async function openProject(path: string) {
    const existing = projects.find((project) => project.path === path)
    if (existing) {
      setInputError(null)
      await selectProject(existing.path)
      return
    }
    try {
      const response = await axios.post<Project>(`${API_BASE_URL}/projects`, { path })
      setInputError(null)
      addProject(response.data)
      await selectProject(response.data.path)
    } catch (requestError) {
      if (axios.isAxiosError<ApiErrorResponse>(requestError)) {
        setInputError(requestError.response?.data.error.message ?? '无法连接后端')
      } else {
        setInputError('创建项目失败')
      }
    }
  }

  function removeProject(path: string) {
    setProjects((current) => current.filter((project) => project.path !== path))
    if (path === activePath) {
      socketRef.current?.close()
      socketRef.current = null
      setActivePath(null)
      setActiveSessionFile(null)
      setMessages([])
      setTotalToken(0)
      setWaiting(false)
      activeMessageIdRef.current = null
      messageCreatedAtRef.current.clear()
    }
  }

  function handleEvent(event: ServerEvent) {
    if (event.type === 'user_message') {
      setMessages((current) => [...current, {
        id: event.id,
        role: 'user',
        content: event.content,
        attachments: event.attachments,
        status: 'complete',
        createdAt: event.createdAt,
      }])
      return
    }
    if (event.type === 'user_message_rejected') {
      setMessages((current) => current.filter((message) => message.id !== event.messageId))
      const rejectedId = activeMessageIdRef.current
      if (rejectedId) {
        messageCreatedAtRef.current.delete(rejectedId)
        activeMessageIdRef.current = null
      }
      setWaiting(false)
      setInputError(event.error.message)
      inputBoxRef.current?.restore(event.content, event.attachments)
      return
    }
    if (event.type === 'message_start') {
      activeMessageIdRef.current = event.messageId
      messageCreatedAtRef.current.set(event.messageId, event.createdAt)
      return
    }
    if (event.type === 'content_delta') {
      setMessages((current) => {
        const last = current.at(-1)
        if (last?.role === 'assistant' && (last.id === event.messageId || last.parentMessageId === event.messageId)) {
          return current.map((item) => item.id === last.id ? { ...item, content: item.content + event.delta } : item)
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
        ...current.map((item) => item.role === 'assistant' && item.parentMessageId === event.messageId && item.status === 'streaming'
          ? { ...item, status: 'complete' as const }
          : item),
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
    if (event.type === 'tool_call_arguments') {
      setMessages((current) => current.map((item) => item.role === 'tool' && item.id === event.toolCallId
        ? { ...item, arguments: event.arguments }
        : item))
      return
    }
    if (event.type === 'tool_call_result') {
      setMessages((current) => current.map((item) => item.role === 'tool' && item.id === event.toolCallId
        ? { ...item, result: event.result, status: event.isError ? 'error' : 'complete' }
        : item))
      return
    }
    if (event.type === 'message_end') {
      setMessages((current) => current.map((item) => (item.id === event.messageId || item.parentMessageId === event.messageId) && item.status === 'streaming'
        ? { ...item, status: 'complete' }
        : item))
      messageCreatedAtRef.current.delete(event.messageId)
      activeMessageIdRef.current = null
      setCompletedMessageId(event.messageId)
      setTotalToken(event.totalToken)
      setWaiting(false)
      return
    }
    setMessages((current) => {
      let foundActiveNode = false
      const updated = current.map((item) => {
        if (item.status !== 'streaming') return item
        foundActiveNode = true
        if (item.role === 'assistant') return { ...item, content: item.content || event.error.message, status: 'error' as const }
        if (item.role === 'tool') return { ...item, result: item.result || event.error.message, status: 'error' as const }
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

  async function startNewSession() {
    if (!activePath || startingSession) return
    setStartingSession(true)
    try {
      const request: NewSessionRequest = { projectPath: activePath }
      const response = await axios.post<NewSessionResponse>(`${API_BASE_URL}/sessions`, request)
      socketRef.current?.close()
      setMessages([])
      setTotalToken(0)
      setCompletedMessageId(null)
      setActiveSessionFile(response.data.sessionFile)
      setSessionRefreshVersion((current) => current + 1)
      setWaiting(false)
      activeMessageIdRef.current = null
      messageCreatedAtRef.current.clear()
      connect(activePath, response.data.sessionFile)
    } finally {
      setStartingSession(false)
    }
  }

  async function selectModel(modelName: string) {
    if (modelName === activeModelName) return
    try {
      await axios.put(`${API_BASE_URL}/models/default`, { modelName })
    } catch {
      return
    }
    setActiveModelName(modelName)
    if (activePath) connect(activePath, activeSessionFile, modelName)
  }

  const responding = waiting || messages.some((message) => message.status === 'streaming')

  async function stop() {
    if (!activePath || !responding) return
    const request: InterruptSessionRequest = { projectPath: activePath }
    await axios.post(`${API_BASE_URL}/sessions/interrupt`, request)
    setMessages((current) => current.map((message) => {
      if (message.status !== 'streaming') return message
      if (message.role === 'tool') {
        return { ...message, result: message.result || '用户中断', status: 'error' as const }
      }
      return {
        ...message,
        content: `${message.content}\n\n[用户中断了本次回答]`,
        status: 'error' as const,
      }
    }))
    setWaiting(false)
    activeMessageIdRef.current = null
    messageCreatedAtRef.current.clear()
    connect(activePath, activeSessionFile)
  }

  function send(content: string, attachments: Attachment[]) {
    const socket = socketRef.current
    if (!socket || socket.readyState !== WebSocket.OPEN || !activePath) return
    const message: ClientMessage = { type: 'message', content, attachments }
    setWaiting(true)
    setInputError(null)
    socket.send(JSON.stringify(message))
  }

  return (
    <div className="app-shell">
      <div className="home-page">
        <header className="home-page__header">
          <strong>{activePath ?? '输入 # 项目路径来添加或切换项目'}</strong>
          <span>{activePath ? (connected ? '已连接' : '连接中…') : '未选择项目'}</span>
        </header>
        <MessageArea
          messages={messages}
          toolsHidden={toolsHidden}
          completedMessageId={completedMessageId}
        />
        <SessionInfo
          modelName={activeModelName}
          responding={responding}
          totalToken={totalToken}
          toolsHidden={toolsHidden}
          onToolsHiddenChange={setToolsHidden}
        />
        <InputBox
          chatDisabled={!activePath || !connected}
          editorDisabled={responding || startingSession}
          error={inputError}
          ref={inputBoxRef}
          files={projectFiles}
          models={models}
          projects={projects}
          skills={skills}
          newSessionDisabled={!activePath || startingSession}
          waiting={responding}
          onModelSelect={selectModel}
          onNewSession={startNewSession}
          onProjectOpen={openProject}
          onSend={send}
          onStop={stop}
        />
      </div>
      <ProjectSidebar
        activePath={activePath}
        activeSessionFile={activeSessionFile}
        collapsed={sidebarCollapsed}
        onRemove={removeProject}
        onSelect={selectProject}
        onSelectSession={selectSession}
        onToggle={() => setSidebarCollapsed((current) => !current)}
        projects={projects}
        sessionRefreshVersion={sessionRefreshVersion}
      />
    </div>
  )
}
