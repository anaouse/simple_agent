import { useEffect, useRef, useState } from 'react'

interface SessionInfoProps {
  modelName: string | null
  responding: boolean
  totalToken: number
}

export default function SessionInfo({ modelName, responding, totalToken }: SessionInfoProps) {
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
      <span>当前模型</span>
      <strong>{modelName ?? '未加载'}</strong>
      <span>当前上下文</span>
      <strong>{totalToken} Token</strong>
      <span>本轮耗时</span>
      <strong>{elapsedSeconds}s</strong>
    </div>
  )
}
