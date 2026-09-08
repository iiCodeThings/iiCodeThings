# 会话菜单与 /new-session Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 会话行只留三横线菜单；去掉「新对话」按钮；发送以 `/new-session` 开头的内容则新建会话（可选标题）。

**Architecture:** `parseNewSessionCommand` 纯函数识别命令。Composer 在无模型时也允许发出该命令。AppShell 拦截后 `createSession` + 可选 `patchSession`。会话操作统一为已有 `session-actions menu`，触发器用 `Icon name="menu"`。

**Tech Stack:** Vue 3、Vitest。

## Global Constraints

- 桌面和窄屏：标题旁只留三横线，菜单项不变。
- 去掉所有「新对话」按钮。
- `trim` 后以 `/new-session` 开头（大小写敏感）才算命令；标题为去掉前缀再 trim 的剩余；空则默认「新对话」。
- 命令不发模型、不上传附件、不要求已选模型。
- 不改后端默认标题与「标题仍为新对话则首次消息自动命名」。
- 不增加其它斜杠命令。
- 规范：`docs/superpowers/specs/2026-09-08-session-menu-and-new-session-design.md`。
- 走 TDD。用户未要求时不要 `git commit`。

---

## File Structure

```
frontend/src/newSessionCommand.js
frontend/src/newSessionCommand.test.js
frontend/src/layout.js
frontend/src/layout.test.js
frontend/src/components/AppShell.vue
frontend/src/components/Composer.vue
frontend/src/views/ChatView.vue
frontend/src/styles.css
```

---

### Task 1: `parseNewSessionCommand`

**Files:**
- Create: `frontend/src/newSessionCommand.js`
- Create: `frontend/src/newSessionCommand.test.js`

**Interfaces:**
- Consumes: 无
- Produces: `parseNewSessionCommand(raw) -> { title: string | null } | null`
  - `trim` 后不以 `/new-session` 开头 → `null`
  - 开头匹配 → `{ title }`：去掉前缀 `/new-session` 再 `trim`，空字符串则 `title: null`（表示用默认「新对话」）

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/newSessionCommand.test.js`:

```javascript
import { describe, expect, it } from 'vitest'
import { parseNewSessionCommand } from './newSessionCommand.js'

describe('parseNewSessionCommand', () => {
  it('returns null when not a command', () => {
    expect(parseNewSessionCommand('')).toBe(null)
    expect(parseNewSessionCommand('hello')).toBe(null)
    expect(parseNewSessionCommand('/NEW-SESSION')).toBe(null)
    expect(parseNewSessionCommand('x /new-session')).toBe(null)
  })

  it('treats prefix match as a command', () => {
    expect(parseNewSessionCommand('/new-session')).toEqual({ title: null })
    expect(parseNewSessionCommand('  /new-session  ')).toEqual({ title: null })
    expect(parseNewSessionCommand('/new-session   ')).toEqual({ title: null })
    expect(parseNewSessionCommand('/new-session 韦伯笔记')).toEqual({ title: '韦伯笔记' })
    expect(parseNewSessionCommand('/new-sessionfoo')).toEqual({ title: 'foo' })
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- src/newSessionCommand.test.js`

Expected: FAIL（模块不存在）

- [ ] **Step 3: Write minimal implementation**

Create `frontend/src/newSessionCommand.js`:

```javascript
export const NEW_SESSION_PREFIX = '/new-session'

export function parseNewSessionCommand(raw) {
  const text = String(raw ?? '').trim()
  if (!text.startsWith(NEW_SESSION_PREFIX)) return null
  const rest = text.slice(NEW_SESSION_PREFIX.length).trim()
  return { title: rest === '' ? null : rest }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- src/newSessionCommand.test.js`

Expected: PASS

- [ ] **Step 5: Skip commit**（用户未要求）

---

### Task 2: 统一三横线菜单并去掉「新对话」按钮

**Files:**
- Modify: `frontend/src/layout.js`
- Modify: `frontend/src/layout.test.js`
- Modify: `frontend/src/components/AppShell.vue`
- Modify: `frontend/src/views/ChatView.vue`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: 现有 `session-actions menu` 与 `Icon name="menu"`
- Produces:
  - `sessionActionsMode(_narrow) -> 'menu'`（恒为 `'menu'`，参数可忽略）
  - AppShell 只渲染一套 menu；触发器 `aria-label="会话操作"`，内含 `<Icon name="menu" />`，无「更多」、无 `session-actions icons`、无「新对话」按钮
  - 桌面也能看见菜单按钮：`.session-actions.menu { display: flex }`（不要再 `display: none`）
  - ChatView 占位：`选择左侧会话，或发送 /new-session 开始`

- [ ] **Step 1: Rewrite the failing layout tests**

In `frontend/src/layout.test.js` replace `describe('sessionActionsMode'` with:

```javascript
describe('sessionActionsMode', () => {
  it('always uses the menu', () => {
    expect(sessionActionsMode(true)).toBe('menu')
    expect(sessionActionsMode(false)).toBe('menu')
  })
})
```

Replace `describe('narrow session more menu'` first two tests with:

```javascript
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
```

Keep the existing `closes the menu at the start of each session action` and `unclips the session list` tests inside this describe.

Delete the test `defines .more-session outside the narrow media query` entirely.

Keep `chat topbar stacking` describe unchanged except it must still pass after removing the topbar 新对话 button (no assertion currently requires that button).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- src/layout.test.js`

Expected: FAIL（仍有 icons / 新对话 / 更多 / sessionActionsMode(false)==='icons'）

- [ ] **Step 3: Implement**

`frontend/src/layout.js`:

```javascript
export function sessionActionsMode(_narrow) {
  return 'menu'
}
```

`AppShell.vue` template:

- Delete both `<button ... class="new-chat" ...>新对话</button>` (aside and topbar).
- Delete the entire `<span v-if="sessionActionsMode(narrow) === 'icons'" class="session-actions icons">...</span>`.
- Change the remaining block from `v-else class="session-actions menu"` to always `class="session-actions menu"`.
- Replace the 「更多」 button with:

```html
                <button
                  type="button"
                  class="icon-btn"
                  aria-label="会话操作"
                  title="会话操作"
                  @click.stop="menuOpenId = menuOpenId === s.id ? null : s.id"
                >
                  <Icon name="menu" />
                </button>
```

Keep the `ul.session-menu` as-is.

`onNewChat` may remain for Task 3 to reuse, or delete if unused after removing buttons — **keep `onNewChat` until Task 3** so create-session logic stays in one place. If eslint unused, Task 3 will call it; until then prefix is unused. **Delete `onNewChat` in this task** and recreate the create+select flow in Task 3's `onComposerSend` to avoid unused function. Prefer: **keep `onNewChat` as `async function onNewChat(title)`** used only in Task 3. If unused after this task, `npm run build` still succeeds (Vue SFC unused script bindings are fine). Leave `onNewChat` in place for Task 3.

`ChatView.vue` placeholder `<p>`:

```html
      <p>选择左侧会话，或发送 /new-session 开始</p>
```

`styles.css`:

Change `.session-actions.menu` from `display: none` to:

```css
.session-actions.menu {
  display: flex;
  position: relative;
}
```

Remove the narrow-media rule `.session-list .session-actions.icons { display: none; }` if present.

Remove unused `.more-session { ... }` rule if nothing references it.

Narrow `.chat-topbar .new-chat { ... }` can stay or be deleted; delete it if present to avoid dead CSS.

Keep `.session-list .session-actions.menu { opacity: 1 }` in the narrow media query.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- src/layout.test.js && npm test && npm run build`

Expected: PASS；build 成功

- [ ] **Step 5: Skip commit**（用户未要求）

---

### Task 3: 发送 `/new-session` 建会话

**Files:**
- Modify: `frontend/src/components/Composer.vue`
- Modify: `frontend/src/components/AppShell.vue`

**Interfaces:**
- Consumes: `parseNewSessionCommand` from `frontend/src/newSessionCommand.js`；现有 `createSession`、`patchSession`、`loadSessions`
- Produces: Composer 在命令时不检查 `modelId`、不要求附件、仍 emit `send`；AppShell `onComposerSend` 若为命令则建会话（可选 PATCH 标题截断 128）、选中、关抽屉、回 `/`，**不**调用 `viewRef.send`

- [ ] **Step 1: Composer — skip model check for the command**

In `frontend/src/components/Composer.vue` import:

```javascript
import { parseNewSessionCommand } from '../newSessionCommand.js'
```

Replace `onSend` with:

```javascript
function onSend() {
  const text = content.value
  if (parseNewSessionCommand(text)) {
    emit('send', { content: text, files: [], enableThinking: enableThinking.value })
    content.value = ''
    files.value = null
    if (fileInput.value) fileInput.value.value = ''
    return
  }
  if (!props.modelId) {
    alert('请先在设置中添加模型')
    return
  }
  const fileList = files.value
  if (!text.trim() && (!fileList || fileList.length === 0)) return
  const snapshot = fileList ? [...fileList] : []
  emit('send', { content: text, files: snapshot, enableThinking: enableThinking.value })
  content.value = ''
  files.value = null
  if (fileInput.value) fileInput.value.value = ''
}
```

- [ ] **Step 2: AppShell intercept**

Import `parseNewSessionCommand`. Replace `onNewChat` with a version that accepts an optional title, used by the command path:

```javascript
async function onNewChat(title) {
  const s = await createSession()
  if (title) {
    await patchSession(s.id, title.slice(0, 128))
  }
  await loadSessions()
  currentId.value = s.id
  menuOpenId.value = null
  setDrawer('select')
  if (route.path !== '/') router.push('/')
}
```

Replace the start of `onComposerSend`:

```javascript
async function onComposerSend({ content, files, enableThinking }) {
  const cmd = parseNewSessionCommand(content)
  if (cmd) {
    await onNewChat(cmd.title)
    return
  }
  if (!modelId.value) {
    alert('请先在设置中添加模型')
    return
  }
  if (route.path !== '/') {
    await router.push('/')
    await nextTick()
  }
  if (!currentId.value) {
    const s = await createSession()
    await loadSessions()
    currentId.value = s.id
    await nextTick()
  }
  await nextTick()
  await viewRef.value?.send({ content, files, modelId: modelId.value, enableThinking })
}
```

`cmd.title` is `string | null`; `onNewChat(null)` must not PATCH. Use `if (title)` so `null` skips PATCH.

- [ ] **Step 3: Regression**

Run: `cd frontend && npm test && npm run build`

Expected: 全部前端测试 PASS（含 `newSessionCommand.test.js`、`composerKeys.test.js`）；build 成功。不改后端。

- [ ] **Step 4: Skip commit**（用户未要求）

---

## Spec coverage

| Spec | Task |
|------|------|
| `parseNewSessionCommand` 与用例 | 1 |
| 三横线菜单、无 icons、无「更多」、无「新对话」 | 2 |
| `sessionActionsMode` 恒为 menu；桌面能看见菜单 | 2 |
| 占位文案 | 2 |
| 命令不发模型、不上传、不要求模型；可选标题；切会话 | 3 |
| 不改后端默认标题 | （未改后端） |
