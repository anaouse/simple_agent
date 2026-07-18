import axios from 'axios'
import { FormEvent, useState } from 'react'
import ProjectItem from '@/components/ProjectItem'
import type { ApiErrorResponse, Project } from '@/types'

const API_URL = `${location.protocol}//${location.hostname}:2453/api/projects`

interface ProjectSidebarProps {
  activePath: string | null
  activeSessionFile: string | null
  collapsed: boolean
  projects: Project[]
  sessionRefreshVersion: number
  onAdd: (project: Project) => void
  onSelect: (path: string) => void | Promise<void>
  onSelectSession: (path: string, fileName: string) => void | Promise<void>
  onToggle: () => void
}

export default function ProjectSidebar({
  activePath,
  activeSessionFile,
  collapsed,
  projects,
  sessionRefreshVersion,
  onAdd,
  onSelect,
  onSelectSession,
  onToggle,
}: ProjectSidebarProps) {
  const [path, setPath] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    const value = path.trim()
    if (!value || submitting) return
    setSubmitting(true)
    setError('')
    try {
      const response = await axios.post<Project>(API_URL, { path: value })
      onAdd(response.data)
      setPath('')
    } catch (requestError) {
      if (axios.isAxiosError<ApiErrorResponse>(requestError)) {
        setError(requestError.response?.data.error.message ?? '无法连接后端')
      } else {
        setError('创建项目失败')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <aside className={`project-sidebar${collapsed ? ' project-sidebar--collapsed' : ''}`}>
      <button
        aria-label={collapsed ? '展开侧边栏' : '收起侧边栏'}
        className="project-sidebar__toggle"
        onClick={onToggle}
        type="button"
      >
        {collapsed ? '›' : '‹'}
      </button>
      {!collapsed && (
        <div className="project-sidebar__content">
          <h2>项目</h2>
          <form className="project-sidebar__form" onSubmit={submit}>
            <input
              aria-label="项目文件夹路径"
              disabled={submitting}
              onChange={(event) => setPath(event.target.value)}
              placeholder="D:/projects/daily"
              value={path}
            />
            <button disabled={submitting || !path.trim()} type="submit">确认</button>
          </form>
          {error && <p className="project-sidebar__error">{error}</p>}
          <div className="project-sidebar__list">
            {projects.map((project) => (
              <ProjectItem
                activePath={activePath}
                activeSessionFile={activeSessionFile}
                key={project.path}
                onSelectProject={onSelect}
                onSelectSession={onSelectSession}
                project={project}
                refreshVersion={sessionRefreshVersion}
              />
            ))}
          </div>
        </div>
      )}
    </aside>
  )
}
