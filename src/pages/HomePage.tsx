import axios from 'axios'
import { useEffect, useRef, useState } from 'react'
import InputBox from '@/components/InputBox'
import MessageArea from '@/components/MessageArea'
import ProjectSidebar from '@/components/ProjectSidebar'
import type {
  ChatMessage,
  ClientMessage,
  NewSessionRequest,
  NewSessionResponse,
  OpenSessionRequest,
  Project,
  ProjectFileEntry,
  ProjectFilesEvent,
  ServerEvent,
  SessionResponse,
} from '@/types'

const API_BASE_URL = `${location.protocol}//${location.hostname}:2453/api`
const WS_BASE_URL = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.hostname}:2453/ws/chat`
const FILES_WS_BASE_URL = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.hostname}:2453/ws/project-files`
const PROJECTS_STORAGE_KEY = 'agent-projects'

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

export default function HomePage() {
  const [projects, setProjects] = useState<Project[]>(loadProjects)
  const [activePath, setActivePath] = useState<string | null>(null)
  const [activeSessionFile, setActiveSessionFile] = useState<string | null>(null)
  const [sessionRefreshVersion, setSessionRefreshVersion] = useState(0)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [projectFiles, setProjectFiles] = useState<ProjectFileEntry[]>([])
  const [connected, setConnected] = useState(false)
  const [waiting, setWaiting] = useState(false)
  const [startingSession, setStartingSession] = useState(false)
  const socketRef = useRef<WebSocket | null>(null)
  const activeMessageIdRef = useRef<string | null>(null)
  const messageCreatedAtRef = useRef(new Map<string, string>())

  useEffect(() => {
    localStorage.setItem(PROJECTS_STORAGE_KEY, JSON.stringify(projects))
  }, [projects])

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

  function connect(path: string, sessionFile?: string | null) {
    socketRef.current?.close()
    setConnected(false)
    setWaiting(false)
    const query = new URLSearchParams({ project_path: path })
    if (sessionFile) query.set('session_file', sessionFile)
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
    activeMessageIdRef.current = null
    messageCreatedAtRef.current.clear()
    setActivePath(path)
    let sessionFile: string | null = null
    try {
      const response = await axios.get<SessionResponse>(`${API_BASE_URL}/sessions/current`, {
        params: { project_path: path },
      })
      setMessages(response.data.messages)
      sessionFile = response.data.sessionFile
      setActiveSessionFile(sessionFile)
    } catch {
      setMessages([])
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

  function handleEvent(event: ServerEvent) {
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

  function send(content: string) {
    const socket = socketRef.current
    if (!socket || socket.readyState !== WebSocket.OPEN || !activePath) return
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
    <div className="app-shell">
      <ProjectSidebar
        activePath={activePath}
        activeSessionFile={activeSessionFile}
        collapsed={sidebarCollapsed}
        onAdd={addProject}
        onSelect={selectProject}
        onSelectSession={selectSession}
        onToggle={() => setSidebarCollapsed((current) => !current)}
        projects={projects}
        sessionRefreshVersion={sessionRefreshVersion}
      />
      <div className="home-page">
        <header className="home-page__header">
          <strong>{activePath ?? '请在侧边栏创建或选择一个项目'}</strong>
          <span>{activePath ? (connected ? '已连接' : '连接中…') : '未选择项目'}</span>
        </header>
        <MessageArea messages={messages} />
        <InputBox
          disabled={!activePath || !connected || waiting || startingSession}
          files={projectFiles}
          newSessionDisabled={!activePath || startingSession}
          onNewSession={startNewSession}
          onSend={send}
        />
      </div>
    </div>
  )
}
