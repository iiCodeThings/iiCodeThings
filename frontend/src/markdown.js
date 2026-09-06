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

const WRAP_PAIRS = [
  ['“', '”'],
  ['‘', '’'],
  ['「', '」'],
  ['『', '』'],
  ['（', '）'],
  ['【', '】'],
  ['《', '》'],
  ['〈', '〉'],
  ['〔', '〕'],
  ['(', ')'],
  ['"', '"'],
  ["'", "'"],
]

const EMPHASIS_MARKERS = ['***', '___', '**', '__', '*', '_']

function escapeRe(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function unwrapPunctEmphasis(text) {
  let result = text
  for (const marker of EMPHASIS_MARKERS) {
    const m = escapeRe(marker)
    const pre = marker.includes('*') ? '(?<!\\*)' : '(?<!_)'
    const post = marker.includes('*') ? '(?!\\*)' : '(?!_)'
    for (const [open, close] of WRAP_PAIRS) {
      const re = new RegExp(
        `${pre}${m}${escapeRe(open)}([^\\n]*?)${escapeRe(close)}${m}${post}`,
        'g',
      )
      result = result.replace(re, `${open}${marker}$1${marker}${close}`)
    }
  }
  return result
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
  const prepared = mapOutsideCode(String(src || ''), unwrapPunctEmphasis)
  const html = String(marked.parse(prepared, { async: false, gfm: true, breaks: true }))
  const p = getPurify()
  const cleaned = p
    ? p.sanitize(html, {
        USE_PROFILES: { html: true },
        ADD_ATTR: ['target', 'rel'],
      })
    : html
  return stripScripts(String(cleaned))
}
