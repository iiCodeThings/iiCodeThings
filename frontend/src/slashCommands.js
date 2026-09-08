export const SLASH_COMMANDS = [
  { id: 'new-session', command: '/new-session', hint: '新建会话' },
  { id: 'search', command: '/search', hint: '打开搜索' },
]

export const SEARCH_PREFIX = '/search'

export function slashCommandDraft(raw) {
  const text = String(raw ?? '').trimStart()
  if (!text.startsWith('/')) return null
  if (text.includes(' ')) return null
  return text
}

export function matchSlashCommands(draft, commands = SLASH_COMMANDS) {
  if (draft == null || draft === '') return []
  return commands.filter((c) => c.command.startsWith(draft))
}

export function completeSlashCommand(command) {
  return `${command} `
}

export function parseSearchCommand(raw) {
  const text = String(raw ?? '').trim()
  if (!text.startsWith(SEARCH_PREFIX)) return null
  return { ok: true }
}
