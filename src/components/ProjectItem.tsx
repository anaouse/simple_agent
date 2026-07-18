import axios from 'axios'
import { useEffect, useState } from 'react'
import type { Project, SessionListResponse, SessionSummary } from '@/types'

const API_URL = `${location.protocol}//${location.hostname}:2453/api/sessions`

interface ProjectItemProps {
  activePath: string | null
  activeSessionFile: string | null
  project: Project
  refreshVersion: number
  onSelectProject: (path: string) => void | Promise<void>
  onSelectSession: (path: string, fileName: string) => void | Promise<void>
}

export default function ProjectItem({
  activePath,
  activeSessionFile,
  project,
  refreshVersion,
  onSelectProject,
  onSelectSession,
}: ProjectItemProps) {
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const active = project.path === activePath

  useEffect(() => {
    if (!active) return
    axios.get<SessionListResponse>(API_URL, { params: { project_path: project.path } })
      .then((response) => setSessions(response.data.sessions))
      .catch(() => setSessions([]))
  }, [active, project.path, refreshVersion])

  return (
    <div className="project-item">
      <button
        className={active ? 'project-sidebar__item project-sidebar__item--active' : 'project-sidebar__item'}
        onClick={() => onSelectProject(project.path)}
        title={project.path}
        type="button"
      >
        {project.path}
      </button>
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
