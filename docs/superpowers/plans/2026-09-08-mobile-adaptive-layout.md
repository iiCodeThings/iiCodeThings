# 移动端自适应布局 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 视口 &lt; 720px 时聊天全宽、会话列表用左侧抽屉；桌面两栏不变；其它单栏页只收紧留白和点按区域。

**Architecture:** 纯前端。`layout.js` 提供断点与抽屉开关纯函数；`AppShell` 用 `matchMedia('(max-width: 719.98px)')` 切换顶栏/抽屉。窄屏会话操作用「更多」菜单。样式用同一断点的 `@media`。

**Tech Stack:** Vue 3、Vue Router、Vitest、CSS `@media` / `dvh` / `env(safe-area-inset-*)`。

## Global Constraints

- 视口宽度 **&lt; 720px**：聊天全宽，会话列表从左侧以覆盖层打开。
- 视口宽度 **≥ 720px**：仍是现在的左右栏，行为不变。
- 断点：`720px`（CSS `max-width: 719.98px` 为窄屏）。窗口拉过断点时关掉抽屉。
- 主壳高度：`100dvh`，不支持时回退 `100vh`。
- viewport 增加 `viewport-fit=cover`；顶栏、抽屉、输入条加 `safe-area-inset-*`。
- 不做独立 App、PWA、手势滑抽屉、系统式返回栈。
- 不把 `/search` 接进主界面导航。
- 不改后端 API、不改发送快捷键、不改搜索/分享/只读页的跳转规则。
- 不把会话操作改成滑动删除。
- 规范：`docs/superpowers/specs/2026-09-08-mobile-adaptive-layout-design.md`。
- 走 TDD。用户未要求时不要 `git commit`。

---

## File Structure

```
frontend/src/layout.js
frontend/src/layout.test.js
frontend/index.html
frontend/src/styles.css
frontend/src/components/Icons.vue
frontend/src/components/AppShell.vue
frontend/src/components/Composer.vue
```

---

### Task 1: 断点与抽屉状态纯函数

**Files:**
- Create: `frontend/src/layout.js`
- Create: `frontend/src/layout.test.js`

**Interfaces:**
- Consumes: 无
- Produces:
  - `NARROW_QUERY = '(max-width: 719.98px)'`
  - `isNarrowViewport(widthPx) -> boolean`（`Number(widthPx) < 720`）
  - `sessionActionsMode(narrow) -> 'icons' | 'menu'`（`narrow` 为真 → `'menu'`）
  - `nextDrawerOpen({ open, narrow, action }) -> boolean`
    - `narrow` 为假 → 恒 `false`（含 `action: 'widen'`）
    - `action: 'toggle'` → `!open`
    - `action` 为 `'close' | 'select' | 'escape' | 'backdrop'` → `false`
    - `action: 'open'` → `true`
    - 其它 → `open`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/layout.test.js`:

```javascript
import { describe, expect, it } from 'vitest'
import {
  NARROW_QUERY,
  isNarrowViewport,
  nextDrawerOpen,
  sessionActionsMode,
} from './layout.js'

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- src/layout.test.js`

Expected: FAIL（`layout.js` 不存在）

- [ ] **Step 3: Write minimal implementation**

Create `frontend/src/layout.js`:

```javascript
export const NARROW_QUERY = '(max-width: 719.98px)'

export function isNarrowViewport(widthPx) {
  return Number(widthPx) < 720
}

export function sessionActionsMode(narrow) {
  return narrow ? 'menu' : 'icons'
}

export function nextDrawerOpen({ open, narrow, action }) {
  if (!narrow) return false
  if (action === 'toggle') return !open
  if (action === 'open') return true
  if (
    action === 'close' ||
    action === 'select' ||
    action === 'escape' ||
    action === 'backdrop' ||
    action === 'widen'
  ) {
    return false
  }
  return open
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- src/layout.test.js`

Expected: PASS

- [ ] **Step 5: Skip commit**（用户未要求）

---

### Task 2: viewport-fit、高度、safe-area 与窄屏壳 CSS

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `NARROW_QUERY` 的媒体条件字符串（CSS 手写同样的 `max-width: 719.98px`）
- Produces: 窄屏下左栏可变为 fixed 抽屉、顶栏可显示；桌面规则不改选择器含义。本任务只加 CSS / meta，不改 Vue 结构（下一任务才挂 class）。

- [ ] **Step 1: Viewport meta**

In `frontend/index.html` replace the viewport meta with:

```html
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
```

- [ ] **Step 2: Shell height and narrow layout CSS**

In `frontend/src/styles.css` change `.shell` to:

```css
.shell {
  display: flex;
  height: 100vh;
  height: 100dvh;
}
```

After `.settings-link.router-link-active` block (before `.right`), append. If that landmark moved, append immediately after the existing `.shell` / `.left` / `.right` desktop rules so desktop selectors stay intact:

```css
.chat-topbar {
  display: none;
}

.drawer-backdrop {
  display: none;
}

@media (max-width: 719.98px) {
  .chat-topbar {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    flex-shrink: 0;
    min-height: 48px;
    padding: 0.45rem 0.75rem;
    padding-top: calc(0.45rem + env(safe-area-inset-top, 0px));
    padding-left: calc(0.75rem + env(safe-area-inset-left, 0px));
    padding-right: calc(0.75rem + env(safe-area-inset-right, 0px));
    border-bottom: 1px solid var(--paper-line);
    background: var(--paper);
  }

  .chat-topbar .topbar-title {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 1rem;
    font-weight: 600;
  }

  .chat-topbar .new-chat {
    width: auto;
    flex-shrink: 0;
    padding: 0.4rem 0.7rem;
    min-height: 44px;
  }

  .chat-topbar .icon-btn {
    width: 44px;
    height: 44px;
    flex-shrink: 0;
  }

  .drawer-backdrop {
    display: none;
    position: fixed;
    inset: 0;
    z-index: 15;
    border: 0;
    padding: 0;
    background: rgba(28, 46, 38, 0.35);
  }

  .shell.drawer-open .drawer-backdrop {
    display: block;
  }

  .left {
    position: fixed;
    z-index: 20;
    top: 0;
    left: 0;
    bottom: 0;
    width: min(292px, 86vw);
    transform: translateX(-100%);
    transition: transform 0.22s ease;
    padding-top: env(safe-area-inset-top, 0px);
    padding-bottom: env(safe-area-inset-bottom, 0px);
    padding-left: env(safe-area-inset-left, 0px);
    box-shadow: none;
  }

  .shell.drawer-open .left {
    transform: translateX(0);
    box-shadow: 8px 0 28px rgba(36, 42, 34, 0.18);
  }

  .right {
    width: 100%;
    flex: 1;
  }

  .composer {
    padding-bottom: calc(0.85rem + env(safe-area-inset-bottom, 0px));
    padding-left: calc(0.75rem + env(safe-area-inset-left, 0px));
    padding-right: calc(0.75rem + env(safe-area-inset-right, 0px));
  }

  .composer-box textarea {
    min-height: 2.6rem;
  }

  .composer-actions {
    flex-wrap: wrap;
  }

  .icon-btn.attach,
  .send-btn {
    min-height: 44px;
    min-width: 44px;
  }

  .think-toggle {
    min-height: 44px;
  }

  .session-list .session-actions.icons {
    display: none;
  }

  .session-list .session-actions.menu {
    display: flex;
  }

  .more-btn {
    width: 44px;
    height: 44px;
  }

  .login-page,
  .settings,
  .search-page,
  .share-page {
    padding-left: max(0.9rem, env(safe-area-inset-left, 0px));
    padding-right: max(0.9rem, env(safe-area-inset-right, 0px));
  }

  .share-article {
    padding-top: 1.6rem;
    padding-bottom: 2.2rem;
  }
}
```

Default `.session-actions.menu { display: none; }` on desktop — add **outside** the media query, next to `.session-actions`:

```css
.session-actions.menu {
  display: none;
  position: relative;
}

.session-menu {
  position: absolute;
  right: 0;
  top: 100%;
  z-index: 4;
  margin: 0;
  padding: 0.25rem 0;
  list-style: none;
  min-width: 9.5rem;
  background: var(--cream);
  border: 1px solid var(--paper-line);
  border-radius: 10px;
  box-shadow: var(--shadow);
}

.session-menu button {
  display: block;
  width: 100%;
  text-align: left;
  border: 0;
  background: transparent;
  padding: 0.55rem 0.8rem;
  min-height: 44px;
  font: inherit;
  font-size: 0.88rem;
  color: var(--ink);
  cursor: pointer;
}

.session-menu button:hover,
.session-menu button:focus {
  background: rgba(36, 85, 68, 0.08);
}

.session-menu button.danger {
  color: var(--danger);
}
```

Inside the existing `@media (max-width: 719.98px)` keep `.session-list .session-actions.menu { display: flex; }`.

- [ ] **Step 3: Regression**

Run: `cd frontend && npm test && npm run build`

Expected: tests PASS；build 成功

- [ ] **Step 4: Skip commit**（用户未要求）

---

### Task 3: AppShell 顶栏与抽屉

**Files:**
- Modify: `frontend/src/components/Icons.vue`
- Modify: `frontend/src/components/AppShell.vue`

**Interfaces:**
- Consumes: `NARROW_QUERY`、`nextDrawerOpen` from `frontend/src/layout.js`
- Produces:
  - `narrow`：`matchMedia(NARROW_QUERY).matches`
  - `drawerOpen`：仅窄屏可为 true；`onSelect` / 遮罩 / Esc / 汉堡用 `nextDrawerOpen`
  - 窄屏 `.shell` 带 `drawer-open` class；顶栏标题为当前 session 的 `title`，否则 `'对话'`
  - 打开抽屉时 `document.body.style.overflow = 'hidden'`，关闭或变宽时清掉

- [ ] **Step 1: Add hamburger icon**

In `frontend/src/components/Icons.vue`, after the `link` svg block (the last `v-else-if`), add:

```vue
    v-else-if="name === 'menu'"
```

Full svg:

```vue
  <svg
    v-else-if="name === 'menu'"
    class="icon"
    viewBox="0 0 24 24"
    fill="none"
    aria-hidden="true"
  >
    <path
      d="M5 7h14M5 12h14M5 17h14"
      stroke="currentColor"
      stroke-width="1.55"
      stroke-linecap="round"
    />
  </svg>
```

- [ ] **Step 2: Wire shell state**

In `frontend/src/components/AppShell.vue` script, add imports:

```javascript
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
```

```javascript
import { NARROW_QUERY, nextDrawerOpen, sessionActionsMode } from '../layout.js'
```

After existing refs, add:

```javascript
const narrow = ref(false)
const drawerOpen = ref(false)
const menuOpenId = ref(null)

const currentTitle = computed(() => {
  const row = sessions.value.find((s) => s.id === currentId.value)
  return row?.title || '对话'
})

function setDrawer(action) {
  drawerOpen.value = nextDrawerOpen({
    open: drawerOpen.value,
    narrow: narrow.value,
    action,
  })
}

function onHamburger() {
  setDrawer('toggle')
}

function onBackdrop() {
  setDrawer('backdrop')
}

function onDrawerKey(e) {
  if (e.key === 'Escape') {
    setDrawer('escape')
    menuOpenId.value = null
  }
}

function onDocPointer(e) {
  if (menuOpenId.value == null) return
  const el = e.target
  if (el && typeof el.closest === 'function' && el.closest('.session-actions.menu')) return
  menuOpenId.value = null
}
```

Change `onSelect`:

```javascript
function onSelect(s) {
  currentId.value = s.id
  menuOpenId.value = null
  setDrawer('select')
  if (route.path !== '/') router.push('/')
}
```

`onNewChat` after setting `currentId` also `setDrawer('select')` and `menuOpenId.value = null`.

In `onMounted`, after the existing `Promise.all` load, register media + listeners. Combine with existing onMounted rather than a second one:

```javascript
onMounted(async () => {
  try {
    await Promise.all([loadSessions(), loadModels()])
  } catch {
    /* 401 redirects via jsonFetch */
  }
  const mq = window.matchMedia(NARROW_QUERY)
  const apply = () => {
    narrow.value = mq.matches
    if (!mq.matches) setDrawer('widen')
  }
  apply()
  mq.addEventListener('change', apply)
  window.addEventListener('keydown', onDrawerKey)
  document.addEventListener('pointerdown', onDocPointer)
  onUnmounted(() => {
    mq.removeEventListener('change', apply)
    window.removeEventListener('keydown', onDrawerKey)
    document.removeEventListener('pointerdown', onDocPointer)
    document.body.style.overflow = ''
  })
})
```

`onUnmounted` inside `onMounted` is valid in Vue 3. Prefer a sibling `onUnmounted` that stores `mq`/`apply` in `let mq` outside if the file already has a clean setup — use lets at script top:

```javascript
let narrowMq = null

function applyNarrow() {
  if (!narrowMq) return
  narrow.value = narrowMq.matches
  if (!narrowMq.matches) setDrawer('widen')
}

onMounted(async () => {
  try {
    await Promise.all([loadSessions(), loadModels()])
  } catch {
    /* 401 redirects via jsonFetch */
  }
  narrowMq = window.matchMedia(NARROW_QUERY)
  applyNarrow()
  narrowMq.addEventListener('change', applyNarrow)
  window.addEventListener('keydown', onDrawerKey)
  document.addEventListener('pointerdown', onDocPointer)
})

onUnmounted(() => {
  if (narrowMq) narrowMq.removeEventListener('change', applyNarrow)
  window.removeEventListener('keydown', onDrawerKey)
  document.removeEventListener('pointerdown', onDocPointer)
  document.body.style.overflow = ''
})
```

Watch drawer for body scroll:

```javascript
watch([drawerOpen, narrow], ([open, isNarrow]) => {
  document.body.style.overflow = open && isNarrow ? 'hidden' : ''
})
```

- [ ] **Step 3: Template**

Replace the root `<div class="shell">` opening with:

```html
  <div class="shell" :class="{ 'drawer-open': drawerOpen && narrow }">
    <button
      v-show="narrow && drawerOpen"
      type="button"
      class="drawer-backdrop"
      aria-label="关闭会话列表"
      @click="onBackdrop"
    ></button>
    <aside class="left">
```

Leave the existing aside inner (brand, new-chat, session list, nav-foot) in place. Session list actions are Task 4 — do not replace icons yet in this task if it would break desktop; Task 4 immediately follows. **This task may leave session icons as they are.**

Before `<main class="right">` inner RouterView, insert top bar as first child of `.right`:

```html
    <main class="right">
      <header v-show="narrow" class="chat-topbar">
        <button type="button" class="icon-btn" aria-label="会话列表" @click="onHamburger">
          <Icon name="menu" />
        </button>
        <span class="topbar-title">{{ currentTitle }}</span>
        <button type="button" class="new-chat" @click="onNewChat">新对话</button>
      </header>
      <RouterView v-slot="{ Component }">
```

`v-show="narrow"` keeps layout logic in JS; CSS also hides `.chat-topbar` by default. Both is OK: CSS `display:none` on desktop, `v-show` false also works if matchMedia lags first paint. Rely on CSS `@media` for showing `.chat-topbar { display: flex }` AND always render the header in DOM (remove `v-show`, let CSS hide it). **Render the header unconditionally**; CSS hides it ≥720px so SSR/first paint is fine even before matchMedia.

Final header:

```html
      <header class="chat-topbar">
        <button type="button" class="icon-btn" aria-label="会话列表" @click="onHamburger">
          <Icon name="menu" />
        </button>
        <span class="topbar-title">{{ currentTitle }}</span>
        <button type="button" class="new-chat" @click="onNewChat">新对话</button>
      </header>
```

- [ ] **Step 4: Regression**

Run: `cd frontend && npm test && npm run build`

Expected: PASS；build 成功（含新 `menu` icon）

- [ ] **Step 5: Skip commit**（用户未要求）

---

### Task 4: 窄屏会话「更多」菜单

**Files:**
- Modify: `frontend/src/components/AppShell.vue`

**Interfaces:**
- Consumes: `sessionActionsMode(narrow)` → `'icons' | 'menu'`；`menuOpenId` from Task 3
- Produces: 窄屏每行一个「更多」；菜单项：置顶或取消置顶、重命名、分享会话、用 AI 生成标题、删除。点项后关菜单。桌面仍是六个 `icon-btn`。

- [ ] **Step 1: Split actions in the session `<li>`**

Replace the existing `<span class="session-actions">...</span>` with two blocks. Keep every existing `@click` handler (`onUnpin`, `onPin`, `onRename`, `onShareSession`, `onAiTitle`, `onDelete`) unchanged (they already `stopPropagation`).

```html
            <div class="session-head">
              <span class="session-title" :title="s.title">{{ s.title }}</span>
              <span v-if="sessionActionsMode(narrow) === 'icons'" class="session-actions icons">
                <button
                  v-if="s.pinned"
                  type="button"
                  class="icon-btn"
                  title="取消置顶"
                  aria-label="取消置顶"
                  @click="onUnpin(s, $event)"
                >
                  <Icon name="unpin" />
                </button>
                <button type="button" class="icon-btn" title="置顶" aria-label="置顶" @click="onPin(s, $event)">
                  <Icon name="pin" />
                </button>
                <button type="button" class="icon-btn" title="重命名" aria-label="重命名" @click="onRename(s, $event)">
                  <Icon name="quill" />
                </button>
                <button
                  type="button"
                  class="icon-btn"
                  title="分享会话"
                  aria-label="分享会话"
                  @click="onShareSession(s, $event)"
                >
                  <Icon name="link" />
                </button>
                <button
                  type="button"
                  class="icon-btn"
                  title="用 AI 生成标题"
                  aria-label="用 AI 生成标题"
                  :disabled="retitlingId != null"
                  @click="onAiTitle(s, $event)"
                >
                  <span v-if="retitlingId === s.id" class="msg-spinner" aria-hidden="true"></span>
                  <Icon v-else name="spark" />
                </button>
                <button type="button" class="icon-btn danger" title="删除" aria-label="删除" @click="onDelete(s, $event)">
                  <Icon name="inkx" />
                </button>
              </span>
              <span v-else class="session-actions menu">
                <button
                  type="button"
                  class="icon-btn"
                  aria-label="更多"
                  title="更多"
                  @click.stop="menuOpenId = menuOpenId === s.id ? null : s.id"
                >
                  更多
                </button>
                <ul v-if="menuOpenId === s.id" class="session-menu">
                  <li>
                    <button v-if="s.pinned" type="button" @click="onUnpin(s, $event)">取消置顶</button>
                    <button v-else type="button" @click="onPin(s, $event)">置顶</button>
                  </li>
                  <li>
                    <button type="button" @click="onRename(s, $event)">重命名</button>
                  </li>
                  <li>
                    <button type="button" @click="onShareSession(s, $event)">分享会话</button>
                  </li>
                  <li>
                    <button type="button" :disabled="retitlingId != null" @click="onAiTitle(s, $event)">
                      用 AI 生成标题
                    </button>
                  </li>
                  <li>
                    <button type="button" class="danger" @click="onDelete(s, $event)">删除</button>
                  </li>
                </ul>
              </span>
            </div>
```

The 「更多」button currently uses `class="icon-btn"` with text; CSS `icon-btn` is 28×28 and will clip. Add class `more-session` instead:

```html
                <button
                  type="button"
                  class="more-session"
                  aria-label="更多"
                  @click.stop="menuOpenId = menuOpenId === s.id ? null : s.id"
                >
                  更多
                </button>
```

Add to `frontend/src/styles.css` (desktop default, not inside media):

```css
.more-session {
  flex-shrink: 0;
  border: 0;
  background: transparent;
  color: var(--pine);
  font: inherit;
  font-size: 0.78rem;
  padding: 0.35rem 0.4rem;
  min-height: 44px;
  cursor: pointer;
}
```

After each menu action, close the menu. Add at the start of `onPin`, `onUnpin`, `onRename`, `onShareSession`, `onAiTitle`, `onDelete`:

```javascript
  menuOpenId.value = null
```

(Those functions already take `(s, ev)` and call `ev.stopPropagation()`.)

- [ ] **Step 2: Confirm layout tests still express the mode split**

Run: `cd frontend && npm test -- src/layout.test.js`

Expected: `sessionActionsMode(true) === 'menu'` PASS

- [ ] **Step 3: Full frontend regression**

Run: `cd frontend && npm test && npm run build`

Expected: PASS；build 成功

- [ ] **Step 4: Skip commit**（用户未要求）

---

### Task 5: 输入框与其它页收尾

**Files:**
- Modify: `frontend/src/styles.css`（Task 2 已含 composer / more-btn / 单栏 padding；本任务只补缺口）
- Modify: `frontend/src/components/Composer.vue` 仅当 `rows="3"` 在窄屏仍撑得太高：把 textarea 的 `rows` 改为 `2`（桌面仍靠 CSS `min-height: 4.4rem` 保持约 3 行视觉高度）

**Interfaces:**
- Consumes: Task 2 media rules
- Produces: 窄屏输入约 2 行；附件/推理/发送 ≥44px；登录/设置/搜索/分享无横向滚动；搜索 `.more-btn` 44px；不改 `shouldSendOnKeydown`

- [ ] **Step 1: Composer rows**

In `frontend/src/components/Composer.vue` change textarea to `rows="2"`. Desktop `.composer-box textarea { min-height: 4.4rem; }` already keeps taller field.

- [ ] **Step 2: Fill any missing media tweaks**

If Task 2 already added composer wrap, 44px targets, search `.more-btn`, login/settings/search/share padding, and share-article padding, do not duplicate. If `.settings` still has large horizontal padding only from desktop `1.4rem 1.5rem`, the Task 2 rule `.settings { padding-left/right: max(0.9rem, env(...)) }` overrides left/right; leave top as-is.

Ensure `.search-omnibox` can shrink:

```css
@media (max-width: 719.98px) {
  .search-omnibox {
    font-size: 1rem;
  }

  .message-pane {
    padding-left: 0.85rem;
    padding-right: 0.85rem;
  }
}
```

Merge into the existing `@media (max-width: 719.98px)` block rather than a second copy of the same query if possible.

- [ ] **Step 3: Regression**

Run:

```
cd frontend && npm test && npm run build
```

Expected: 全部既有前端测试 PASS（含 `composerKeys.test.js`）；build 成功。不改后端。

- [ ] **Step 4: Skip commit**（用户未要求）

---

## Spec coverage

| Spec | Task |
|------|------|
| &lt; 720px 聊天全宽 + 左侧覆盖列表；≥ 720px 两栏不变 | 1, 2, 3 |
| CSS `719.98px` / 拉宽关掉抽屉 | 1, 3 |
| `100dvh` 回退 `100vh`；`viewport-fit=cover`；safe-area | 2 |
| 顶栏：汉堡、标题、「新对话」 | 3 |
| 遮罩 / 汉堡 / Esc / 选会话关抽屉；锁滚动 | 1, 3 |
| 抽屉内仍有新对话；设置在右栏全宽；`currentId` 不丢 | 3（现有 `currentId` + RouterView） |
| 桌面图标 / 窄屏「更多」菜单 | 1, 4 |
| 输入仍在聊天底；约 2 行；44px；换行；不改快捷键 | 2, 5 |
| 登录/设置/搜索/只读留白与点按；搜索跳转不变 | 2, 5 |
| 不做 PWA / 手势 / `/search` 进导航 / 后端改动 | （未改那些） |
