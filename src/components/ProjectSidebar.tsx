import ProjectItem from '@/components/ProjectItem'
import type { Project } from '@/types'

interface ProjectSidebarProps {
  activePath: string | null
  activeSessionFile: string | null
  collapsed: boolean
  projects: Project[]
  sessionRefreshVersion: number
  onRemove: (path: string) => void
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
  onRemove,
  onSelect,
  onSelectSession,
  onToggle,
}: ProjectSidebarProps) {
  return (
    <aside className={`project-sidebar${collapsed ? ' project-sidebar--collapsed' : ''}`}>
      <button
        aria-label={collapsed ? '展开侧边栏' : '收起侧边栏'}
        className="project-sidebar__toggle"
        onClick={onToggle}
        type="button"
      >
        {collapsed ? '‹' : '›'}
      </button>
      {!collapsed && (
        <div className="project-sidebar__content">
          <div className="project-sidebar__list">
            {projects.map((project) => (
              <ProjectItem
                activePath={activePath}
                activeSessionFile={activeSessionFile}
                key={project.path}
                onRemoveProject={onRemove}
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
