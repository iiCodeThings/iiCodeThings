export const NEW_SESSION_PREFIX = '/new-session'

export function parseNewSessionCommand(raw) {
  const text = String(raw ?? '').trim()
  if (!text.startsWith(NEW_SESSION_PREFIX)) return null
  const rest = text.slice(NEW_SESSION_PREFIX.length).trim()
  return { title: rest === '' ? null : rest }
}
