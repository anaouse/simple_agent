import { useEffect, useState } from 'react'
import type { Attachment } from '@/types'

interface AttachmentsProps {
  attachments: Attachment[]
  onRemove?: (index: number) => void
}

function dataUrl(attachment: Attachment): string {
  return `data:${attachment.mediaType};base64,${attachment.data}`
}

export default function Attachments({ attachments, onRemove }: AttachmentsProps) {
  const [preview, setPreview] = useState<Attachment | null>(null)

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setPreview(null)
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <>
      <div className="attachments">
        {attachments.map((attachment, index) => (
          <div className="attachment" key={`${attachment.mediaType}-${index}`}>
            <img
              src={dataUrl(attachment)}
              alt=""
              onClick={() => setPreview(attachment)}
            />
            {onRemove && (
              <button
                className="attachment__remove"
                onClick={() => onRemove(index)}
                type="button"
                aria-label="删除图片"
              >
                ×
              </button>
            )}
          </div>
        ))}
      </div>
      {preview && (
        <div className="image-preview" onClick={() => setPreview(null)}>
          <img
            src={dataUrl(preview)}
            alt=""
            onClick={(event) => event.stopPropagation()}
          />
        </div>
      )}
    </>
  )
}
