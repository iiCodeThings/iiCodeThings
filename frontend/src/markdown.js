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

export function renderMarkdown(src) {
  const html = String(marked.parse(src || '', { async: false, gfm: true, breaks: true }))
  const p = getPurify()
  const cleaned = p
    ? p.sanitize(html, {
        USE_PROFILES: { html: true },
        ADD_ATTR: ['target', 'rel'],
      })
    : html
  return stripScripts(String(cleaned))
}
