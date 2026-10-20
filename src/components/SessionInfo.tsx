import { useEffect, useRef, useState } from 'react'

interface SessionInfoProps {
  projectPath: string | null
  connected: boolean
  modelName: string | null
  responding: boolean
  totalToken: number
  toolsHidden: boolean
  onToolsHiddenChange: (hidden: boolean) => void
}

/** 取路径最后一段，用于紧凑显示 */
function lastPathSegment(path: string) {
  const segments = path.split(/[\\/]/).filter(Boolean)
  return segments.at(-1) ?? path
}

export default function SessionInfo({
  projectPath,
  connected,
  modelName,
  responding,
  totalToken,
  toolsHidden,
  onToolsHiddenChange,
}: SessionInfoProps) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const startedAtRef = useRef<number | null>(null)

  useEffect(() => {
    if (!responding) {
      if (startedAtRef.current !== null) {
        setElapsedSeconds(Math.floor((Date.now() - startedAtRef.current) / 1000))
        startedAtRef.current = null
      }
      return
    }

    startedAtRef.current = Date.now()
    setElapsedSeconds(0)
    const timer = window.setInterval(() => {
      if (startedAtRef.current !== null) {
        setElapsedSeconds(Math.floor((Date.now() - startedAtRef.current) / 1000))
      }
    }, 1000)
    return () => window.clearInterval(timer)
  }, [responding])

  return (
    <div className="session-info">
      <div className="session-info__group">
        <strong className="session-info__project" title={projectPath ?? undefined}>
          {projectPath ? lastPathSegment(projectPath) : '未选择项目'}
        </strong>
        <span className="session-info__connection">
          {projectPath ? (connected ? '已连接' : '连接中…') : '未连接'}
        </span>
      </div>
      <div className="session-info__group">
        <strong title="当前模型">{modelName ?? '未加载'}</strong>
        <strong title="当前上下文">{totalToken} Token</strong>
        <strong title="本轮耗时">{elapsedSeconds}s</strong>
        <button
          className="session-info__tools-toggle"
          onClick={() => onToolsHiddenChange(!toolsHidden)}
          type="button"
        >
          {toolsHidden ? '显示工具节点' : '隐藏工具节点'}
        </button>
      </div>
    </div>
  )
}
