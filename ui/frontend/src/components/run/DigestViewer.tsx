import { useMemo } from 'react'
import { parseDigest } from './digestParser'
import DigestCard from './DigestCard'

interface DigestViewerProps {
  content: string
}

export default function DigestViewer({ content }: DigestViewerProps) {
  const sections = useMemo(() => parseDigest(content), [content])

  if (!sections.length) {
    return (
      <div className="text-center py-8 text-apple-gray-400 text-sm">
        No content to display
      </div>
    )
  }

  // Separate header, body, and footer
  const header = sections.find(s => s.isHeader)
  const footer = sections.find(s => s.isFooter)
  const body = sections.filter(s => !s.isHeader && !s.isFooter)

  return (
    <div className="space-y-4">
      {/* Header banner */}
      {header && (
        <div className="card bg-gradient-to-r from-apple-gray-50 to-white">
          <div
            className="digest-data text-center"
            dangerouslySetInnerHTML={{ __html: header.dataHtml }}
          />
        </div>
      )}

      {/* Section cards */}
      {body.map(section => (
        <DigestCard key={section.id} section={section} />
      ))}

      {/* Footer */}
      {footer && (
        <div className="text-center text-sm text-apple-gray-400 py-2">
          <div
            dangerouslySetInnerHTML={{ __html: footer.dataHtml.replace(/─+/g, '') }}
          />
        </div>
      )}
    </div>
  )
}
