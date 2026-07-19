interface SessionInfoProps {
  modelName: string | null
}

export default function SessionInfo({ modelName }: SessionInfoProps) {
  return (
    <div className="session-info">
      <span>当前模型</span>
      <strong>{modelName ?? '未加载'}</strong>
    </div>
  )
}
