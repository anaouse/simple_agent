interface SessionInfoProps {
  modelName: string | null
  totalToken: number
}

export default function SessionInfo({ modelName, totalToken }: SessionInfoProps) {
  return (
    <div className="session-info">
      <span>当前模型</span>
      <strong>{modelName ?? '未加载'}</strong>
      <span>当前对话</span>
      <strong>{totalToken} Token</strong>
    </div>
  )
}
