import createDOMPurify from 'dompurify'
import { marked } from 'marked'

let purify = null

function getPurify() {
  if (purify) return purify
  const view = typeof window !== 'undefined' ? window : undefined
  if (!view || !view.document) return null
  const instance = createDOMPurify(view)
  if (!instance || !instance.isSupported) return null
  instance.addHook('afterSanitizeAttributes', (node) => {
    if (node.tagName === 'A' && node.hasAttribute('href')) {
      node.setAttribute('target', '_blank')
      node.setAttribute('rel', 'noopener noreferrer')
    }
  })
  purify = instance
  return purify
}

function stripScripts(html) {
  return html.replace(/<script\b[\s\S]*?>[\s\S]*?<\/script>/gi, '')
}

const ZWSP = '\u200b'
const PUNCT_RE = /\p{P}/u

function isPunct(ch) {
  return Boolean(ch) && PUNCT_RE.test(ch)
}

function relaxEmphasisFlanking(text) {
  let out = ''
  let i = 0
  while (i < text.length) {
    const ch = text[i]
    if (ch !== '*' && ch !== '_') {
      out += ch
      i += 1
      continue
    }
    let j = i
    while (j < text.length && text[j] === ch) j += 1
    const prev = i > 0 ? text[i - 1] : ''
    const next = j < text.length ? text[j] : ''
    if (isPunct(prev) && !out.endsWith(ZWSP)) out += ZWSP
    out += text.slice(i, j)
    if (isPunct(next)) out += ZWSP
    i = j
  }
  return out
}

function mapOutsideCode(src, transform) {
  const re = /(```[\s\S]*?```|~~~[\s\S]*?~~~|`+[^`]*`+)/g
  let last = 0
  let out = ''
  let match
  while ((match = re.exec(src))) {
    if (match.index > last) out += transform(src.slice(last, match.index))
    out += match[0]
    last = match.index + match[0].length
  }
  if (last < src.length) out += transform(src.slice(last))
  return out
}

export function renderMarkdown(src) {
  const prepared = mapOutsideCode(String(src || ''), relaxEmphasisFlanking)
  const html = String(marked.parse(prepared, { async: false, gfm: true, breaks: true })).replaceAll(
    ZWSP,
    '',
  )
  const p = getPurify()
  const cleaned = p
    ? p.sanitize(html, {
        USE_PROFILES: { html: true },
        ADD_ATTR: ['target', 'rel'],
      })
    : html
  return stripScripts(String(cleaned))
}
