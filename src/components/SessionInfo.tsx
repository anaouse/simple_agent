import { useEffect, useRef, useState } from 'react'

interface SessionInfoProps {
  modelName: string | null
  responding: boolean
  totalToken: number
  toolsHidden: boolean
  onToolsHiddenChange: (hidden: boolean) => void
}

export default function SessionInfo({
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
  )
}
