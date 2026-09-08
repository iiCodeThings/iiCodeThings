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
  it('uses a more menu on narrow, icons on desktop', () => {
    expect(sessionActionsMode(true)).toBe('menu')
    expect(sessionActionsMode(false)).toBe('icons')
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

describe('narrow session more menu', () => {
  it('keeps icon buttons on desktop and a more-session button on narrow', () => {
    expect(appShell).toContain("v-if=\"sessionActionsMode(narrow) === 'icons'\"")
    expect(appShell).toContain('class="session-actions icons"')
    expect(appShell).toContain('class="session-actions menu"')
    const moreBtn = appShell.match(/class="more-session"[\s\S]*?<\/button>/)
    expect(moreBtn).toBeTruthy()
    expect(moreBtn[0]).toContain('aria-label="更多"')
    expect(moreBtn[0]).toMatch(/>\s*更多\s*</)
    expect(moreBtn[0]).not.toContain('icon-btn')
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

  it('defines .more-session outside the narrow media query', () => {
    const rule = `.more-session {
  flex-shrink: 0;
  border: 0;
  background: transparent;
  color: var(--pine);
  font: inherit;
  font-size: 0.78rem;
  padding: 0.35rem 0.4rem;
  min-height: 44px;
  cursor: pointer;
}`
    expect(styles).toContain(rule)
    const ruleIdx = styles.indexOf('.more-session {')
    const mediaIdx = styles.indexOf('@media (max-width: 719.98px)')
    expect(ruleIdx).toBeGreaterThan(-1)
    expect(mediaIdx).toBeGreaterThan(-1)
    expect(ruleIdx).toBeLessThan(mediaIdx)
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
