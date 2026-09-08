import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import {
  NARROW_QUERY,
  isNarrowViewport,
  nextDrawerOpen,
  sessionActionsMode,
} from './layout.js'

const srcDir = dirname(fileURLToPath(import.meta.url))
const appShell = readFileSync(join(srcDir, 'components/AppShell.vue'), 'utf8')
const composer = readFileSync(join(srcDir, 'components/Composer.vue'), 'utf8')
const styles = readFileSync(join(srcDir, 'styles.css'), 'utf8')

function scriptSetup(source) {
  const match = source.match(/<script setup>([\s\S]*?)<\/script>/)
  return match ? match[1] : ''
}

function functionBody(source, name) {
  const match = new RegExp(`(?:async )?function ${name}\\([^)]*\\)\\s*\\{`).exec(source)
  if (!match) return null
  let depth = 1
  let i = match.index + match[0].length
  while (i < source.length && depth > 0) {
    if (source[i] === '{') depth += 1
    else if (source[i] === '}') depth -= 1
    i += 1
  }
  return source.slice(match.index + match[0].length, i - 1)
}

describe('isNarrowViewport', () => {
  it('is true below 720px', () => {
    expect(isNarrowViewport(319)).toBe(true)
    expect(isNarrowViewport(719.98)).toBe(true)
    expect(isNarrowViewport(719.99)).toBe(true)
  })

  it('is false at 720px and above', () => {
    expect(isNarrowViewport(720)).toBe(false)
    expect(isNarrowViewport(1280)).toBe(false)
  })
})

describe('NARROW_QUERY', () => {
  it('matches the CSS breakpoint', () => {
    expect(NARROW_QUERY).toBe('(max-width: 719.98px)')
  })
})

describe('sessionActionsMode', () => {
  it('always uses the menu', () => {
    expect(sessionActionsMode(true)).toBe('menu')
    expect(sessionActionsMode(false)).toBe('menu')
  })
})

describe('nextDrawerOpen', () => {
  it('always closes when not narrow', () => {
    expect(nextDrawerOpen({ open: true, narrow: false, action: 'toggle' })).toBe(false)
    expect(nextDrawerOpen({ open: true, narrow: false, action: 'widen' })).toBe(false)
  })

  it('toggles, opens, and closes on narrow', () => {
    expect(nextDrawerOpen({ open: false, narrow: true, action: 'toggle' })).toBe(true)
    expect(nextDrawerOpen({ open: true, narrow: true, action: 'toggle' })).toBe(false)
    expect(nextDrawerOpen({ open: false, narrow: true, action: 'open' })).toBe(true)
    expect(nextDrawerOpen({ open: true, narrow: true, action: 'select' })).toBe(false)
    expect(nextDrawerOpen({ open: true, narrow: true, action: 'backdrop' })).toBe(false)
    expect(nextDrawerOpen({ open: true, narrow: true, action: 'escape' })).toBe(false)
    expect(nextDrawerOpen({ open: true, narrow: true, action: 'close' })).toBe(false)
  })
})

describe('session actions menu', () => {
  it('uses a single menu with the three-line icon and no icon row or 新对话 buttons', () => {
    expect(appShell).not.toContain('session-actions icons')
    expect(appShell).not.toContain('>新对话<')
    expect(appShell).toContain('class="session-actions menu"')
    expect(appShell).toContain('aria-label="会话操作"')
    expect(appShell).toContain('name="menu"')
    expect(appShell).not.toContain('class="more-session"')
    expect(appShell).not.toMatch(/>\s*更多\s*</)
  })

  it('lists pin, rename, share, AI title, and delete in the more menu', () => {
    const menuBlock = appShell.match(/class="session-actions menu"[\s\S]*?<\/span>/)
    expect(menuBlock).toBeTruthy()
    const html = menuBlock[0]
    expect(html).toContain('取消置顶')
    expect(html).toContain('>置顶<')
    expect(html).toContain('重命名')
    expect(html).toContain('分享会话')
    expect(html).toContain('用 AI 生成标题')
    expect(html).toContain('>删除<')
  })

  it('closes the menu at the start of each session action', () => {
    const script = scriptSetup(appShell)
    for (const name of ['onPin', 'onUnpin', 'onRename', 'onShareSession', 'onAiTitle', 'onDelete']) {
      const body = functionBody(script, name)
      expect(body, name).toBeTruthy()
      expect(body.trim().split('\n')[0].trim(), name).toBe('menuOpenId.value = null')
    }
  })

  it('unclips the session list while a more menu is open', () => {
    expect(appShell).toContain("class=\"session-list\" :class=\"{ 'menu-open': menuOpenId != null }\"")
    expect(styles).toContain(`.session-list.menu-open {
  overflow: visible;
}`)
  })
})

describe('chat topbar stacking and flex', () => {
  it('hides the topbar on desktop with higher specificity than .right > *', () => {
    const hideIdx = styles.indexOf('.right > .chat-topbar {\n  display: none;\n}')
    const starIdx = styles.indexOf('.right > * {')
    expect(hideIdx).toBeGreaterThan(-1)
    expect(starIdx).toBeGreaterThan(-1)
  })

  it('keeps the narrow topbar a horizontal bar above the backdrop', () => {
    const mediaIdx = styles.indexOf('@media (max-width: 719.98px)')
    const media = styles.slice(mediaIdx)
    expect(media).toContain('.right > .chat-topbar {')
    expect(media).toMatch(/flex:\s*0 0 auto/)
    expect(media).toMatch(/flex-direction:\s*row/)
    expect(media).toMatch(/z-index:\s*25/)
    expect(media).toMatch(/position:\s*relative/)
  })
})

describe('narrow drawer settings and more-menu opacity', () => {
  it('closes the drawer when opening settings', () => {
    expect(appShell).toMatch(/<RouterLink[^>]*to="\/settings"[^>]*@click="setDrawer\('close'\)"/)
  })

  it('shows the more action at full opacity on narrow', () => {
    const media = styles.slice(styles.indexOf('@media (max-width: 719.98px)'))
    expect(media).toMatch(/\.session-list \.session-actions\.menu \{[\s\S]*?opacity:\s*1;/)
  })
})

describe('slash command autocomplete', () => {
  it('renders a listbox of slash suggestions above the textarea', () => {
    expect(composer).toContain('class="slash-suggest"')
    expect(composer).toContain('role="listbox"')
    expect(composer).toContain('role="option"')
    expect(composer).toContain('aria-expanded')
    expect(composer).toContain('completeSlashCommand')
    expect(composer).toContain("e.key === 'ArrowDown'")
    expect(composer).toContain("e.key === 'ArrowUp'")
    expect(composer).toContain("e.key === 'Escape'")
    expect(composer).toContain('mousedown.prevent')
  })

  it('places slash-suggest CSS above the composer box', () => {
    expect(styles).toContain('.composer-box {')
    expect(styles).toMatch(/\.composer-box \{[\s\S]*?position:\s*relative;/)
    expect(styles).toContain('.slash-suggest {')
    expect(styles).toMatch(/\.slash-suggest \{[\s\S]*?bottom:\s*100%;/)
  })
})

describe('/new-session intercept', () => {
  it('Composer parses the command before the modelId check and emits empty files', () => {
    const body = functionBody(scriptSetup(composer), 'onSend')
    expect(body).toBeTruthy()
    const parseIdx = body.indexOf('parseNewSessionCommand')
    const searchIdx = body.indexOf('parseSearchCommand')
    const modelIdx = body.indexOf('props.modelId')
    expect(parseIdx).toBeGreaterThan(-1)
    expect(searchIdx).toBeGreaterThan(-1)
    expect(modelIdx).toBeGreaterThan(-1)
    expect(parseIdx).toBeLessThan(modelIdx)
    expect(searchIdx).toBeLessThan(modelIdx)
    expect(body.slice(parseIdx, modelIdx)).toContain('files: []')
    expect(body.slice(searchIdx, modelIdx)).toContain('files: []')
  })

  it('AppShell onComposerSend routes the command to onNewChat without sending to the view', () => {
    const body = functionBody(scriptSetup(appShell), 'onComposerSend')
    expect(body).toBeTruthy()
    expect(body.trim().startsWith('const cmd = parseNewSessionCommand')).toBe(true)
    const newChatIdx = body.indexOf('onNewChat')
    const retIdx = body.indexOf('return', newChatIdx)
    expect(newChatIdx).toBeGreaterThan(-1)
    expect(retIdx).toBeGreaterThan(newChatIdx)
    expect(body.slice(0, retIdx)).not.toContain('viewRef.value?.send')
  })

  it('AppShell onComposerSend routes /search before the model check and does not send', () => {
    const body = functionBody(scriptSetup(appShell), 'onComposerSend')
    expect(body).toBeTruthy()
    const searchIdx = body.indexOf('parseSearchCommand')
    const modelIdx = body.indexOf('modelId.value')
    const sendIdx = body.indexOf('viewRef.value?.send')
    expect(searchIdx).toBeGreaterThan(-1)
    expect(modelIdx).toBeGreaterThan(-1)
    expect(searchIdx).toBeLessThan(modelIdx)
    expect(body.slice(searchIdx, modelIdx)).toContain("router.push('/search')")
    expect(body.slice(searchIdx, modelIdx)).toContain('return')
    expect(body.slice(searchIdx, modelIdx)).not.toContain('viewRef.value?.send')
    expect(sendIdx).toBeGreaterThan(modelIdx)
  })

  it('onNewChat PATCHes a truthy title and still selects if PATCH throws', () => {
    const body = functionBody(scriptSetup(appShell), 'onNewChat')
    expect(body).toBeTruthy()
    const createIdx = body.indexOf('createSession')
    const tryIdx = body.indexOf('try')
    const catchIdx = body.indexOf('catch')
    const finallyIdx = body.indexOf('finally')
    expect(createIdx).toBeGreaterThan(-1)
    expect(tryIdx).toBeGreaterThan(createIdx)
    expect(catchIdx).toBeGreaterThan(tryIdx)
    expect(finallyIdx).toBeGreaterThan(catchIdx)
    const titleGuard = body.match(/if \(title\) \{[\s\S]*?\}/)
    expect(titleGuard).toBeTruthy()
    expect(titleGuard[0]).toContain('patchSession')
    expect(titleGuard[0]).toContain('title.slice(0, 128)')
    expect(body.slice(0, tryIdx)).not.toContain('patchSession')
    expect(body).toMatch(/alert\(e\.message \|\| ['']设置标题失败['']\)/)
    const finallyBody = body.slice(finallyIdx)
    expect(finallyBody).toContain('loadSessions')
    expect(finallyBody).toContain('currentId.value = s.id')
    expect(finallyBody).toContain("setDrawer('select')")
  })
})

describe('narrow session menu trigger', () => {
  it('keeps the last media query and sizes the menu icon-btn to 44px', () => {
    const mediaIdx = styles.indexOf('@media (max-width: 719.98px)')
    expect(mediaIdx).toBeGreaterThan(-1)
    expect(styles.lastIndexOf('@media')).toBe(mediaIdx)
    const media = styles.slice(mediaIdx)
    expect(media).toMatch(
      /\.session-list \.session-actions\.menu \.icon-btn \{[\s\S]*?width:\s*44px;[\s\S]*?height:\s*44px;/,
    )
  })
})
