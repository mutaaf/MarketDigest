/**
 * Parse Telegram HTML digest into structured sections for the rich card viewer.
 */

export interface DigestSection {
  id: string           // slug from title
  emoji: string        // leading emoji character(s)
  title: string        // "QUICK TAKE", "OVERNIGHT RECAP", etc.
  dataHtml: string     // data content (before blockquote)
  analysisHtml: string // blockquote content, if any
  isHeader: boolean    // first fragment (date/time banner)
  isFooter: boolean    // last fragment (after ─── separator)
}

/**
 * Split digest HTML on section separator lines (━━━...) and extract
 * emoji, title, data, and analysis from each fragment.
 */
export function parseDigest(html: string): DigestSection[] {
  if (!html) return []

  // Split on the bold separator line: <b>━━━━━━━━━━━━━━━━━━━━</b>
  const fragments = html.split(/<b>━{10,}<\/b>/)
  const sections: DigestSection[] = []

  for (let i = 0; i < fragments.length; i++) {
    const raw = fragments[i].trim()
    if (!raw) continue

    // First fragment is the header (date/time/title)
    if (i === 0) {
      sections.push({
        id: 'header',
        emoji: '',
        title: '',
        dataHtml: raw,
        analysisHtml: '',
        isHeader: true,
        isFooter: false,
      })
      continue
    }

    // Check if this is the footer (contains ─── separator)
    if (raw.includes('─'.repeat(10))) {
      // Split at the footer separator
      const footerIdx = raw.indexOf('─'.repeat(10))
      const beforeFooter = raw.substring(0, footerIdx).trim()
      const footerContent = raw.substring(footerIdx).trim()

      // Process the section before the footer if it has content
      if (beforeFooter) {
        sections.push(parseFragment(beforeFooter, sections.length))
      }

      // Add footer
      sections.push({
        id: 'footer',
        emoji: '',
        title: '',
        dataHtml: footerContent,
        analysisHtml: '',
        isHeader: false,
        isFooter: true,
      })
      continue
    }

    sections.push(parseFragment(raw, sections.length))
  }

  return sections
}

function parseFragment(raw: string, index: number): DigestSection {
  // Extract title from first <b> line: <b>emoji TITLE TEXT</b>
  const titleMatch = raw.match(/^[\s\n]*<b>([^<]+)<\/b>/)
  let emoji = ''
  let title = ''
  let bodyHtml = raw

  if (titleMatch) {
    const fullTitle = titleMatch[1].trim()
    // Extract leading emoji(s) — emoji chars are typically in specific Unicode ranges
    const emojiMatch = fullTitle.match(/^([\p{Emoji_Presentation}\p{Extended_Pictographic}\uFE0F\u200D]+)\s*/u)
    if (emojiMatch) {
      emoji = emojiMatch[1]
      title = fullTitle.substring(emojiMatch[0].length).trim()
    } else {
      title = fullTitle
    }
    // Remove the title line from body
    bodyHtml = raw.substring(titleMatch[0].length).trim()
  }

  // Split data vs analysis (blockquote)
  let dataHtml = bodyHtml
  let analysisHtml = ''

  const blockquoteMatch = bodyHtml.match(/<blockquote>([\s\S]*?)<\/blockquote>/g)
  if (blockquoteMatch) {
    // Everything before the first blockquote is data
    const firstBqIdx = bodyHtml.indexOf('<blockquote>')
    dataHtml = bodyHtml.substring(0, firstBqIdx).trim()
    // Collect all blockquote contents
    analysisHtml = blockquoteMatch
      .map(bq => bq.replace(/<\/?blockquote>/g, '').trim())
      .join('\n\n')
  }

  const id = title
    ? title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
    : `section-${index}`

  return {
    id,
    emoji,
    title,
    dataHtml,
    analysisHtml,
    isHeader: false,
    isFooter: false,
  }
}
