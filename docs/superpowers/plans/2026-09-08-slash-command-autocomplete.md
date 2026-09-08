# 斜杠命令自动补全 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Composer 输入 `/` 时列出 `/new-session` 与 `/search`，按前缀筛选，点选或 Enter 补全到输入框；发送 `/search` 时跳转搜索页。

**Architecture:** 纯函数模块 `slashCommands.js` 负责草稿判定、前缀匹配、补全字符串与 `parseSearchCommand`。Composer 用该模块渲染输入框上方的 listbox，并处理方向键 / Enter / Esc。AppShell 在现有 `/new-session` 拦截之后拦截 `/search` 并 `router.push('/search')`。

**Tech Stack:** Vue 3、Vitest。

## Global Constraints

- 命令表只有 `/new-session`（新建会话）和 `/search`（打开搜索）；不增加其它斜杠命令。
- 不改 `/new-session` 的建会话/标题规则。
- `/search` 只 `router.push('/search')`，不把剩余文字填进搜索框，不改搜索页。
- 不把 textarea 换成富文本编辑器。
- 不做模糊匹配、拼音、历史命令。
- 命令草稿：`trimStart()` 后以 `/` 开头且其中没有空格才弹出；有空格则关掉。
- 筛选大小写敏感，按 `command` 前缀匹配；无匹配不渲染列表。
- 点选或列表打开时的 Enter：写入 `command + ' '`，不发送、不跳转。
- 发送：先 `/new-session`，否则 `/search`（不调模型、不传附件、不要求已选模型），否则普通消息。
- 规范：`docs/superpowers/specs/2026-09-08-slash-command-autocomplete-design.md`。
- 走 TDD。用户未要求时不要 `git commit`（若走 SDD，SDD 要求每任务提交，SDD 优先）。

---

## File Structure

```
frontend/src/slashCommands.js
frontend/src/slashCommands.test.js
frontend/src/components/Composer.vue
frontend/src/components/AppShell.vue
frontend/src/layout.test.js
frontend/src/styles.css
```

`frontend/src/newSessionCommand.js` 不改。

---

### Task 1: 斜杠命令纯函数

**Files:**
- Create: `frontend/src/slashCommands.js`
- Create: `frontend/src/slashCommands.test.js`

**Interfaces:**
- Consumes: 无
- Produces:
  - `SLASH_COMMANDS`: `[{ id: 'new-session', command: '/new-session', hint: '新建会话' }, { id: 'search', command: '/search', hint: '打开搜索' }]`
  - `slashCommandDraft(raw) -> string | null`
  - `matchSlashCommands(draft, commands = SLASH_COMMANDS) -> typeof SLASH_COMMANDS`（数组，可为空）
  - `completeSlashCommand(command) -> string`（末尾一个空格）
  - `parseSearchCommand(raw) -> { ok: true } | null`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/slashCommands.test.js`:

```javascript
import { describe, expect, it } from 'vitest'
import {
  SLASH_COMMANDS,
  completeSlashCommand,
  matchSlashCommands,
  parseSearchCommand,
  slashCommandDraft,
} from './slashCommands.js'

describe('SLASH_COMMANDS', () => {
  it('lists new-session then search', () => {
    expect(SLASH_COMMANDS.map((c) => c.command)).toEqual(['/new-session', '/search'])
    expect(SLASH_COMMANDS[0].hint).toBe('新建会话')
    expect(SLASH_COMMANDS[1].hint).toBe('打开搜索')
  })
})

describe('slashCommandDraft', () => {
  it('returns the trimStarted slash token when there is no space', () => {
    expect(slashCommandDraft('/')).toBe('/')
    expect(slashCommandDraft('  /n')).toBe('/n')
    expect(slashCommandDraft('/new-session')).toBe('/new-session')
    expect(slashCommandDraft('/s')).toBe('/s')
  })

  it('returns null when not a command draft', () => {
    expect(slashCommandDraft('')).toBe(null)
    expect(slashCommandDraft('hello')).toBe(null)
    expect(slashCommandDraft('/new-session ')).toBe(null)
    expect(slashCommandDraft('/search ')).toBe(null)
    expect(slashCommandDraft('/new-session 韦伯')).toBe(null)
  })
})

describe('matchSlashCommands', () => {
  it('filters by case-sensitive prefix', () => {
    expect(matchSlashCommands('/').map((c) => c.command)).toEqual(['/new-session', '/search'])
    expect(matchSlashCommands('/n').map((c) => c.command)).toEqual(['/new-session'])
    expect(matchSlashCommands('/s').map((c) => c.command)).toEqual(['/search'])
    expect(matchSlashCommands('/N')).toEqual([])
    expect(matchSlashCommands('/foo')).toEqual([])
  })
})

describe('completeSlashCommand', () => {
  it('appends a single trailing space', () => {
    expect(completeSlashCommand('/new-session')).toBe('/new-session ')
    expect(completeSlashCommand('/search')).toBe('/search ')
  })
})

describe('parseSearchCommand', () => {
  it('returns null when not a search command', () => {
    expect(parseSearchCommand('')).toBe(null)
    expect(parseSearchCommand('hello')).toBe(null)
    expect(parseSearchCommand('/SEARCH')).toBe(null)
    expect(parseSearchCommand('/new-session')).toBe(null)
  })

  it('returns a truthy value for /search prefix', () => {
    expect(parseSearchCommand('/search')).toEqual({ ok: true })
    expect(parseSearchCommand('  /search  ')).toEqual({ ok: true })
    expect(parseSearchCommand('/search foo')).toEqual({ ok: true })
    expect(parseSearchCommand('/searchfoo')).toEqual({ ok: true })
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- src/slashCommands.test.js`

Expected: FAIL（模块不存在）

- [ ] **Step 3: Write minimal implementation**

Create `frontend/src/slashCommands.js`:

```javascript
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- src/slashCommands.test.js`

Expected: PASS

- [ ] **Step 5: Skip commit**（用户未要求；SDD 则提交 `feat(frontend): add slash command matching helpers`）

---

### Task 2: Composer 补全列表与键盘

**Files:**
- Modify: `frontend/src/components/Composer.vue`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/layout.test.js`

**Interfaces:**
- Consumes: `SLASH_COMMANDS`、`slashCommandDraft`、`matchSlashCommands`、`completeSlashCommand` from `frontend/src/slashCommands.js`
- Produces: Composer 在命令草稿且有匹配时渲染 `.slash-suggest` listbox；点选 / Enter 把 `content` 设为 `completeSlashCommand(command)`；Esc 与点外部关闭；列表打开时 Enter 不调用 `onSend`

- [ ] **Step 1: Write the failing source-string tests**

In `frontend/src/layout.test.js` add:

```javascript
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
```

Keep existing `/new-session intercept` tests unchanged.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- src/layout.test.js`

Expected: FAIL（Composer 尚无 `slash-suggest`）

- [ ] **Step 3: Implement Composer + CSS**

`frontend/src/components/Composer.vue` — replace the script setup imports and add suggestion state. Full script:

```javascript
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { acceptAttr } from '../api.js'
import { shouldSendOnKeydown } from '../composerKeys.js'
import { parseNewSessionCommand } from '../newSessionCommand.js'
import {
  completeSlashCommand,
  matchSlashCommands,
  slashCommandDraft,
} from '../slashCommands.js'
import Icon from './Icons.vue'

const props = defineProps({
  modelId: { type: [Number, String, null], default: null },
  sessionId: { type: [Number, String, null], default: null },
})

const emit = defineEmits(['send'])

const content = ref('')
const files = ref(null)
const fileInput = ref(null)
const enableThinking = ref(false)
const composerRoot = ref(null)
const suppressSuggest = ref(false)
const highlight = ref(0)

const fileNames = computed(() => {
  const list = files.value
  if (!list || !list.length) return []
  return [...list].map((f) => f.name)
})

const slashMatches = computed(() => {
  if (suppressSuggest.value) return []
  return matchSlashCommands(slashCommandDraft(content.value))
})

const slashOpen = computed(() => slashMatches.value.length > 0)

watch(content, () => {
  suppressSuggest.value = false
})

watch(slashMatches, (rows) => {
  highlight.value = 0
  if (rows.length && highlight.value > rows.length - 1) highlight.value = 0
})

function applySlash(command) {
  content.value = completeSlashCommand(command)
  suppressSuggest.value = true
}

function onFileChange(e) {
  files.value = e.target.files
}

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

function onKeydown(e) {
  if (slashOpen.value) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      highlight.value = Math.min(slashMatches.value.length - 1, highlight.value + 1)
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      highlight.value = Math.max(0, highlight.value - 1)
      return
    }
    if (e.key === 'Enter') {
      e.preventDefault()
      const row = slashMatches.value[highlight.value]
      if (row) applySlash(row.command)
      return
    }
    if (e.key === 'Escape') {
      e.preventDefault()
      suppressSuggest.value = true
      return
    }
  }
  if (!shouldSendOnKeydown(e)) return
  e.preventDefault()
  onSend()
}

function onDocPointer(e) {
  if (!slashOpen.value) return
  const el = e.target
  if (el && typeof el.closest === 'function' && el.closest('.composer')) return
  suppressSuggest.value = true
}

onMounted(() => {
  document.addEventListener('pointerdown', onDocPointer)
})

onUnmounted(() => {
  document.removeEventListener('pointerdown', onDocPointer)
})

defineExpose({ content, files, onSend })
```

`composerRoot` is unused — **do not include it**. The click-outside handler uses `.composer`.

Template: wrap stays `.composer`. Inside `.composer-box`, **before** the textarea, add:

```html
      <ul
        v-if="slashOpen"
        class="slash-suggest"
        role="listbox"
        aria-label="斜杠命令"
      >
        <li
          v-for="(row, i) in slashMatches"
          :key="row.id"
          role="option"
          :aria-selected="i === highlight"
          :class="{ active: i === highlight }"
        >
          <button
            type="button"
            @mousedown.prevent
            @click="applySlash(row.command)"
          >
            <span class="slash-cmd">{{ row.command }}</span>
            <span class="slash-hint">{{ row.hint }}</span>
          </button>
        </li>
      </ul>
```

Textarea: add `:aria-expanded="slashOpen ? 'true' : 'false'"`. Keep `@keydown="onKeydown"` and `v-model="content"`.

`styles.css`:

1. In `.composer-box` add `position: relative;` (keep existing properties).

2. After `.composer-box` block, add:

```css
.slash-suggest {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 100%;
  z-index: 6;
  margin: 0 0 0.35rem;
  padding: 0.25rem 0;
  list-style: none;
  background: var(--cream);
  border: 1px solid var(--paper-line);
  border-radius: 10px;
  box-shadow: var(--shadow);
}

.slash-suggest button {
  display: flex;
  width: 100%;
  align-items: baseline;
  gap: 0.65rem;
  text-align: left;
  border: 0;
  background: transparent;
  padding: 0.55rem 0.8rem;
  min-height: 44px;
  font: inherit;
  cursor: pointer;
}

.slash-suggest li.active button,
.slash-suggest button:hover,
.slash-suggest button:focus {
  background: rgba(36, 85, 68, 0.08);
}

.slash-cmd {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.88rem;
  color: var(--pine);
}

.slash-hint {
  font-size: 0.82rem;
  color: var(--ink-soft);
}
```

3. Inside the existing last `@media (max-width: 719.98px)` block, before the closing `}`, add:

```css
  .slash-suggest button {
    min-height: 44px;
  }
```

Do **not** move that media query; it must remain last in the file.

Remove the unused `watch` branch `if (rows.length && highlight.value > rows.length - 1)` — the reset to `0` is enough. Use only:

```javascript
watch(slashMatches, () => {
  highlight.value = 0
})
```

- [ ] **Step 4: Run tests**

Run: `cd frontend && npm test -- src/layout.test.js && npm test && npm run build`

Expected: PASS；build 成功。若 `aria-expanded` 测试用 `toContain('aria-expanded')` 即可（绑定形式是 `:aria-expanded`）。

- [ ] **Step 5: Skip commit**（SDD 则提交 `feat(frontend): add slash-command autocomplete in the composer`）

---

### Task 3: 发送 `/search` 跳转

**Files:**
- Modify: `frontend/src/components/Composer.vue`
- Modify: `frontend/src/components/AppShell.vue`
- Modify: `frontend/src/layout.test.js`

**Interfaces:**
- Consumes: `parseSearchCommand` from `frontend/src/slashCommands.js`；现有 `parseNewSessionCommand`、`router`
- Produces: Composer 在 `parseSearchCommand` 为真时也不检查 `modelId`、emit `files: []`；AppShell `onComposerSend` 在 `/new-session` 之后、模型检查之前，若 `parseSearchCommand(content)` 则 `router.push('/search')` 并 return，不调用 `viewRef.send`

- [ ] **Step 1: Write the failing intercept tests**

In `frontend/src/layout.test.js`, update the Composer intercept test so **both** command parsers run before `props.modelId`:

```javascript
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
```

Add:

```javascript
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
```

Keep the existing `onComposerSend routes the command to onNewChat` test.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- src/layout.test.js`

Expected: FAIL（尚无 `parseSearchCommand`）

- [ ] **Step 3: Implement intercept**

`Composer.vue` import `parseSearchCommand` from `../slashCommands.js`. Change the start of `onSend`:

```javascript
function onSend() {
  const text = content.value
  if (parseNewSessionCommand(text) || parseSearchCommand(text)) {
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

`AppShell.vue` import `parseSearchCommand` from `../slashCommands.js`. Change `onComposerSend`:

```javascript
async function onComposerSend({ content, files, enableThinking }) {
  const cmd = parseNewSessionCommand(content)
  if (cmd) {
    await onNewChat(cmd.title)
    return
  }
  if (parseSearchCommand(content)) {
    await router.push('/search')
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

Do not change `SearchView.vue`. Do not pass query params.

- [ ] **Step 4: Regression**

Run: `cd frontend && npm test && npm run build`

Expected: 全部前端测试 PASS（含 `slashCommands.test.js`、`newSessionCommand.test.js`、`composerKeys.test.js`）；build 成功。不改后端。

- [ ] **Step 5: Skip commit**（SDD 则提交 `feat(frontend): open /search from the slash command`）

---

## Spec coverage

| Spec | Task |
|------|------|
| `slashCommandDraft` / `matchSlashCommands` / `completeSlashCommand` / `parseSearchCommand` 与用例 | 1 |
| 列表 UI、键盘、Esc、点选补全不发送 | 2 |
| `/search` 发送跳转、不调模型、不填搜索框 | 3 |
| 不改 `/new-session` 建会话规则 | （未改 `newSessionCommand.js` / `onNewChat`） |
| 不增加第三条命令、不改搜索页 | 3 |
