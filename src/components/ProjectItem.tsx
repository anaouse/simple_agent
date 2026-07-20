import axios from 'axios'
import { useEffect, useState } from 'react'
import type { Project, SessionListResponse, SessionSummary } from '@/types'

const BACKEND_PORT = import.meta.env.VITE_BACKEND_PORT || '2453'
const API_URL = `${location.protocol}//${location.hostname}:${BACKEND_PORT}/api/sessions`

interface ProjectItemProps {
  activePath: string | null
  activeSessionFile: string | null
  project: Project
  refreshVersion: number
  onRemoveProject: (path: string) => void
  onSelectProject: (path: string) => void | Promise<void>
  onSelectSession: (path: string, fileName: string) => void | Promise<void>
}

export default function ProjectItem({
  activePath,
  activeSessionFile,
  project,
  refreshVersion,
  onRemoveProject,
  onSelectProject,
  onSelectSession,
}: ProjectItemProps) {
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [menuPosition, setMenuPosition] = useState<{ left: number, top: number } | null>(null)
  const active = project.path === activePath

  useEffect(() => {
    if (!active) return
    axios.get<SessionListResponse>(API_URL, { params: { project_path: project.path } })
      .then((response) => setSessions(response.data.sessions))
      .catch(() => setSessions([]))
  }, [active, project.path, refreshVersion])

  return (
    <div
      className="project-item"
      onContextMenu={(event) => {
        event.preventDefault()
        const bounds = event.currentTarget.getBoundingClientRect()
        setMenuPosition({ left: event.clientX - bounds.left, top: event.clientY - bounds.top })
      }}
    >
      <button
        className={active ? 'project-sidebar__item project-sidebar__item--active' : 'project-sidebar__item'}
        onClick={() => {
          setMenuPosition(null)
          onSelectProject(project.path)
        }}
        title={project.path}
        type="button"
      >
        {project.path}
      </button>
      {menuPosition && (
        <div
          className="project-item__menu"
          onContextMenu={(event) => event.preventDefault()}
          style={menuPosition}
        >
          <button
            className="project-item__delete"
            onClick={() => onRemoveProject(project.path)}
            type="button"
          >
            删除项目
          </button>
        </div>
      )}
      {active && (
        <div className="project-item__sessions">
          {sessions.length === 0 ? (
            <span className="project-item__empty">暂无历史对话</span>
          ) : sessions.map((session) => (
            <button
              className={session.fileName === activeSessionFile
                ? 'project-item__session project-item__session--active'
                : 'project-item__session'}
              key={session.fileName}
              onClick={() => onSelectSession(project.path, session.fileName)}
              title={session.fileName}
              type="button"
            >
              {session.fileName}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
