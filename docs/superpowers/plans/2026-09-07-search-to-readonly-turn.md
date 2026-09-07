# 搜索结果打开一问一答 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 点搜索命中打开需登录的这一问一答；用户另点「生成分享链接」才创建公开 `/s/:token`。

**Architecture:** `find_turn` 从任意消息 id 定位问（及随后的答）。鉴权 `GET /api/sessions/{id}/turns/{message_id}` 只读、不写 `shares`。前端 `/r/:sessionId/:messageId` 与公开 `ShareView` 共用文章组件；分享仍走现有 `shareTurn`。

**Tech Stack:** FastAPI、SQLAlchemy、pytest、Vue 3、Vue Router、Vitest。

## Global Constraints

- 打开 `/r/...` 或 `GET .../turns/...` 都不写入 `shares`、不生成 token。
- 不改 `GET /api/search`、`GET /api/search/messages` 的返回字段。
- 不接线里闲置的 `hitMessageId`，不把搜索结果接回聊天页。
- 不改 `POST .../share`、`POST .../share/turn` 的入参与语义。
- 生成链接后复制 URL，不自动跳到 `/s/:token`。
- 404 文案：会话已删 → 后端 `会话不存在`；找不到这一轮 → 后端 `这一轮不存在`。前端只读页对任何 404 显示「这一轮不存在」。
- 规范：`docs/superpowers/specs/2026-09-07-search-to-readonly-turn-design.md`。
- 走 TDD。用户未要求时不要 `git commit`。

---

## File Structure

```
backend/app/services/turns.py          # find_turn + public_message
backend/app/routers/sessions.py        # GET /{session_id}/turns/{message_id}
backend/app/routers/shares.py          # turn 分享改为调用 find_turn
backend/tests/test_turns.py            # find_turn 与 GET turn
backend/tests/test_shares.py           # 现有用例应仍通过

frontend/src/turnPath.js               # /r/{sessionId}/{messageId}
frontend/src/turnPath.test.js
frontend/src/api.js                    # fetchTurn
frontend/src/api.test.js
frontend/src/components/ShareArticle.vue
frontend/src/views/ShareView.vue
frontend/src/views/OwnerTurnView.vue
frontend/src/views/SearchView.vue
frontend/src/main.js
frontend/src/styles.css
```

---

### Task 1: `find_turn` 与 `public_message`

**Files:**
- Create: `backend/app/services/turns.py`
- Create: `backend/tests/test_turns.py`
- Modify: `backend/app/routers/shares.py`（先只把 `_public_message` 改成从 `turns` 导入，逻辑仍内联；下一任务再换 `find_turn`）

**Interfaces:**
- Consumes: `app.tables.Message`，SQLAlchemy `Session`
- Produces:
  - `public_message(msg: Message) -> dict`（无 `reasoning`；`attachments` 为 `{kind, original_filename}`）
  - `find_turn(db, session_id: int, message_id: int) -> tuple[Message, Message | None] | None`
    - 问在前，答可 `None`
    - 消息不存在、不属于 `session_id`、答找不到对应的问、role 不是 user/assistant → `None`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_turns.py`:

```python
from app.services.turns import find_turn, public_message
from app.tables import ChatSession, Message, Share


def _session(db, title="韦伯笔记"):
    row = ChatSession(title=title)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _msg(db, session_id, role, content, reasoning=None):
    m = Message(
        session_id=session_id,
        role=role,
        content=content,
        reasoning=reasoning,
        model_name="Display",
        model="api-id",
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def test_find_turn_from_user_or_assistant_is_same_pair(db):
    s = _session(db)
    q = _msg(db, s.id, "user", "韦伯是谁？")
    a = _msg(db, s.id, "assistant", "一位社会学家。", reasoning="secret")
    from_user = find_turn(db, s.id, q.id)
    from_asst = find_turn(db, s.id, a.id)
    assert from_user is not None and from_asst is not None
    assert from_user[0].id == from_asst[0].id == q.id
    assert from_user[1].id == from_asst[1].id == a.id


def test_find_turn_question_without_answer(db):
    s = _session(db)
    q = _msg(db, s.id, "user", "只有问")
    found = find_turn(db, s.id, q.id)
    assert found is not None
    assert found[0].id == q.id
    assert found[1] is None


def test_find_turn_missing_or_wrong_session(db):
    a = _session(db)
    b = _session(db)
    q = _msg(db, a.id, "user", "问")
    assert find_turn(db, a.id, 99999) is None
    assert find_turn(db, b.id, q.id) is None


def test_find_turn_assistant_without_user(db):
    s = _session(db)
    a = _msg(db, s.id, "assistant", "孤儿答")
    assert find_turn(db, s.id, a.id) is None


def test_public_message_omits_reasoning(db):
    s = _session(db)
    a = _msg(db, s.id, "assistant", "答", reasoning="secret")
    out = public_message(a)
    assert out["role"] == "assistant"
    assert out["content"] == "答"
    assert out["model_name"] == "Display"
    assert "reasoning" not in out
    assert out["attachments"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. pytest tests/test_turns.py -v`

Expected: FAIL（`app.services.turns` 不存在或函数未定义）

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/services/turns.py`:

```python
from sqlalchemy.orm import Session, selectinload

from app.tables import Message


def public_message(msg: Message) -> dict:
    return {
        "role": msg.role,
        "content": msg.content or "",
        "model_name": msg.model_name,
        "attachments": [
            {"kind": a.kind, "original_filename": a.original_filename} for a in msg.attachments
        ],
    }


def find_turn(
    db: Session, session_id: int, message_id: int
) -> tuple[Message, Message | None] | None:
    msg = (
        db.query(Message)
        .options(selectinload(Message.attachments))
        .filter(Message.id == message_id)
        .first()
    )
    if msg is None or msg.session_id != session_id:
        return None
    if msg.role == "user":
        user_id = msg.id
    elif msg.role == "assistant":
        prev = (
            db.query(Message)
            .filter(
                Message.session_id == session_id,
                Message.id < msg.id,
                Message.role == "user",
            )
            .order_by(Message.id.desc())
            .first()
        )
        if prev is None:
            return None
        user_id = prev.id
    else:
        return None
    user = (
        db.query(Message)
        .options(selectinload(Message.attachments))
        .filter(Message.id == user_id)
        .first()
    )
    if user is None:
        return None
    asst = (
        db.query(Message)
        .options(selectinload(Message.attachments))
        .filter(
            Message.session_id == session_id,
            Message.id > user.id,
            Message.role == "assistant",
        )
        .order_by(Message.id.asc())
        .first()
    )
    return user, asst
```

In `backend/app/routers/shares.py` delete `_public_message` and import:

```python
from app.services.turns import public_message
```

Replace every `_public_message(` with `public_message(`。`_resolve_share` 的内联 turn 查询不动（Task 3 再换）。

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. pytest tests/test_turns.py tests/test_shares.py -v`

Expected: PASS

- [ ] **Step 5: Skip commit**（用户未要求）

---

### Task 2: 鉴权 `GET /api/sessions/{id}/turns/{message_id}`

**Files:**
- Modify: `backend/app/routers/sessions.py`
- Modify: `backend/tests/test_turns.py`

**Interfaces:**
- Consumes: `find_turn`、`public_message`、`get_live_session`、`get_current_user`
- Produces: `GET /api/sessions/{session_id}/turns/{message_id}` JSON：

```python
{
    "title": str,
    "kind": "turn",
    "user_message_id": int,
    "messages": [public_message(...), ...],  # 无答则只有问
}
```

- 未登录 401；会话已删 404 `会话不存在`；`find_turn` 为 `None` 404 `这一轮不存在`
- 不写 `shares` 表

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_turns.py`:

```python
from app.db import seed_default_user
from app.security import hash_password
from app.tables import Share


def _login(client, db, settings):
    seed_default_user(db, settings.app_username, hash_password(settings.app_password))
    client.post("/api/auth/login", json={"username": "admin", "password": "passpass"})


def test_get_turn_from_user_or_assistant(client, db, settings):
    _login(client, db, settings)
    session_id = client.post("/api/sessions").json()["id"]
    client.patch(f"/api/sessions/{session_id}", json={"title": "韦伯笔记"})
    q = _msg(db, session_id, "user", "韦伯是谁？")
    a = _msg(db, session_id, "assistant", "一位社会学家。", reasoning="secret")

    via_q = client.get(f"/api/sessions/{session_id}/turns/{q.id}")
    via_a = client.get(f"/api/sessions/{session_id}/turns/{a.id}")
    assert via_q.status_code == 200
    assert via_a.status_code == 200
    assert via_q.json()["kind"] == "turn"
    assert via_q.json()["title"] == "韦伯笔记"
    assert via_q.json()["user_message_id"] == via_a.json()["user_message_id"] == q.id
    assert [m["content"] for m in via_q.json()["messages"]] == ["韦伯是谁？", "一位社会学家。"]
    assert via_q.json()["messages"] == via_a.json()["messages"]
    assert "reasoning" not in via_q.json()["messages"][1]
    assert db.query(Share).count() == 0


def test_get_turn_question_only(client, db, settings):
    _login(client, db, settings)
    session_id = client.post("/api/sessions").json()["id"]
    q = _msg(db, session_id, "user", "只有问")
    r = client.get(f"/api/sessions/{session_id}/turns/{q.id}")
    assert r.status_code == 200
    assert len(r.json()["messages"]) == 1
    assert r.json()["user_message_id"] == q.id


def test_get_turn_requires_login(client, db):
    s = _session(db)
    q = _msg(db, s.id, "user", "问")
    r = client.get(f"/api/sessions/{s.id}/turns/{q.id}")
    assert r.status_code in (401, 403)


def test_get_turn_404s(client, db, settings):
    _login(client, db, settings)
    a = client.post("/api/sessions").json()["id"]
    b = client.post("/api/sessions").json()["id"]
    q = _msg(db, a, "user", "问")
    lone = client.post("/api/sessions").json()["id"]
    orphan = _msg(db, lone, "assistant", "孤儿答")
    assert client.get(f"/api/sessions/{a}/turns/99999").status_code == 404
    wrong = client.get(f"/api/sessions/{b}/turns/{q.id}")
    assert wrong.status_code == 404
    assert wrong.json()["detail"] == "这一轮不存在"
    missing_user = client.get(f"/api/sessions/{lone}/turns/{orphan.id}")
    assert missing_user.status_code == 404
    assert missing_user.json()["detail"] == "这一轮不存在"
    client.delete(f"/api/sessions/{a}")
    gone = client.get(f"/api/sessions/{a}/turns/{q.id}")
    assert gone.status_code == 404
    assert gone.json()["detail"] == "会话不存在"
```

`_session` / `_msg` 留在文件顶部，供新旧测试共用。孤儿答必须放在**没有** user 消息的会话里，否则 `find_turn` 会命中前面的问。

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. pytest tests/test_turns.py::test_get_turn_from_user_or_assistant tests/test_turns.py::test_get_turn_question_only tests/test_turns.py::test_get_turn_requires_login tests/test_turns.py::test_get_turn_404s -v`

Expected: FAIL（404 路由不存在）

- [ ] **Step 3: Write minimal implementation**

In `backend/app/routers/sessions.py` add imports:

```python
from app.services.turns import find_turn, public_message
```

Add endpoint（放在 `patch_session` 一类 `/{session_id}/...` 路由旁）:

```python
@router.get("/{session_id}/turns/{message_id}")
def get_turn(
    session_id: int,
    message_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = get_live_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    found = find_turn(db, session.id, message_id)
    if found is None:
        raise HTTPException(status_code=404, detail="这一轮不存在")
    user_msg, asst = found
    messages = [user_msg] + ([asst] if asst else [])
    return {
        "title": session.title,
        "kind": "turn",
        "user_message_id": user_msg.id,
        "messages": [public_message(m) for m in messages],
    }
```

`HTTPException` 已在 `sessions.py` 从 fastapi 导入。

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. pytest tests/test_turns.py -v`

Expected: PASS

- [ ] **Step 5: Skip commit**（用户未要求）

---

### Task 3: 公开 turn 分享改走 `find_turn`

**Files:**
- Modify: `backend/app/routers/shares.py`（`_resolve_share` 的 `kind != session` 分支）

**Interfaces:**
- Consumes: `find_turn(db, session.id, row.user_message_id)`
- Produces: `GET /api/shares/{token}` 在 `kind === turn` 时消息列表与 Task 1 规则相同；失败仍 404「分享不存在」

- [ ] **Step 1: Write the failing test**（行为应已被现有用例覆盖；加一条「无答仍可分享」防止回归）

Add to `backend/tests/test_shares.py`:

```python
def test_turn_share_question_without_answer(client, db, settings):
    _login(client, db, settings)
    session_id = client.post("/api/sessions").json()["id"]
    user = Message(
        session_id=session_id,
        role="user",
        content="只有问",
        model_name="Display",
        model="api-id",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = client.post(
        f"/api/sessions/{session_id}/share/turn",
        json={"user_message_id": user.id},
    ).json()["token"]
    client.cookies.clear()
    data = client.get(f"/api/shares/{token}").json()
    assert data["kind"] == "turn"
    assert [m["content"] for m in data["messages"]] == ["只有问"]
```

- [ ] **Step 2: Run existing turn share tests**

Run: `cd backend && PYTHONPATH=. pytest tests/test_shares.py -v`

Expected: `test_turn_share_question_without_answer` 在重构前也应 PASS（当前内联逻辑已支持无答）。此步确认基线为绿。

- [ ] **Step 3: Replace inline turn lookup**

In `_resolve_share`，`kind == "session"` 分支保持 `q.all()`。else 改为：

```python
        found = find_turn(db, session.id, row.user_message_id)
        if found is None:
            raise HTTPException(status_code=404, detail="分享不存在")
        user_msg, asst = found
        messages = [user_msg] + ([asst] if asst else [])
```

删除 else 里原来的 `user = db.query...` / `asst = db.query...`。把 import 改成：

```python
from app.services.turns import find_turn, public_message
```

session 分支仍需要原来的 `q` 查询；把 `q = db.query(Message)...` 挪进 `if row.kind == "session"` 内，避免无用查询。

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. pytest tests/test_shares.py tests/test_turns.py -v`

Expected: PASS

- [ ] **Step 5: Skip commit**（用户未要求）

---

### Task 4: `turnPath` 与 `fetchTurn`

**Files:**
- Create: `frontend/src/turnPath.js`
- Create: `frontend/src/turnPath.test.js`
- Modify: `frontend/src/api.js`
- Modify: `frontend/src/api.test.js`

**Interfaces:**
- Consumes: `jsonFetch`
- Produces:
  - `turnPath(sessionId, messageId) -> string` 例如 `turnPath(3, 9) === '/r/3/9'`
  - `fetchTurn(sessionId, messageId)` → `GET /api/sessions/{id}/turns/{messageId}`；404 throw `这一轮不存在`；其它非 2xx throw `无法打开`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/turnPath.test.js`:

```javascript
import { describe, expect, it } from 'vitest'
import { turnPath } from './turnPath.js'

describe('turnPath', () => {
  it('builds /r/{sessionId}/{messageId}', () => {
    expect(turnPath(3, 9)).toBe('/r/3/9')
    expect(turnPath('3', '9')).toBe('/r/3/9')
  })
})
```

Add to `frontend/src/api.test.js`:

```javascript
import { afterEach, describe, expect, it } from 'vitest'
import { acceptAttr, fetchTurn } from './api.js'

describe('fetchTurn', () => {
  const orig = globalThis.fetch
  afterEach(() => {
    globalThis.fetch = orig
  })

  it('GETs /api/sessions/:id/turns/:messageId', async () => {
    globalThis.fetch = async (url, opts) => {
      expect(url).toBe('/api/sessions/3/turns/9')
      expect(opts.credentials).toBe('include')
      return {
        status: 200,
        ok: true,
        json: async () => ({ kind: 'turn', user_message_id: 8, messages: [] }),
      }
    }
    const data = await fetchTurn(3, 9)
    expect(data.user_message_id).toBe(8)
  })

  it('throws 这一轮不存在 on 404', async () => {
    globalThis.fetch = async () => ({ status: 404, ok: false, json: async () => ({}) })
    await expect(fetchTurn(1, 2)).rejects.toThrow('这一轮不存在')
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- src/turnPath.test.js src/api.test.js`

Expected: FAIL（`turnPath` / `fetchTurn` 未定义）

- [ ] **Step 3: Write minimal implementation**

Create `frontend/src/turnPath.js`:

```javascript
export function turnPath(sessionId, messageId) {
  return `/r/${sessionId}/${messageId}`
}
```

In `frontend/src/api.js` after `fetchShare`:

```javascript
export async function fetchTurn(sessionId, messageId) {
  const res = await jsonFetch(`/api/sessions/${sessionId}/turns/${messageId}`)
  if (res.status === 404) throw new Error('这一轮不存在')
  if (!res.ok) throw new Error('无法打开')
  return res.json()
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- src/turnPath.test.js src/api.test.js`

Expected: PASS

- [ ] **Step 5: Skip commit**（用户未要求）

---

### Task 5: 抽出 `ShareArticle`，`ShareView` 改用它

**Files:**
- Create: `frontend/src/components/ShareArticle.vue`
- Modify: `frontend/src/views/ShareView.vue`

**Interfaces:**
- Consumes: `title`、`kind`、`messages`、`footer`；可选 slot `header-extra`
- Produces: 与现有公开分享页相同的文章 DOM（kicker、标题、问/答、附件、页脚）

- [ ] **Step 1: No isolated Vue test**（仓库 vitest `environment: 'node'`，无组件挂载。）本任务用现有 `ShareView` 结构做提取，下一步 `npm test` 与 `npm run build` 作回归。

- [ ] **Step 2: Create `ShareArticle.vue`**

```vue
<script setup>
import { renderMarkdown } from '../markdown.js'

defineProps({
  title: { type: String, default: '' },
  kind: { type: String, default: 'turn' },
  messages: { type: Array, default: () => [] },
  footer: { type: String, default: '只读分享' },
})
</script>

<template>
  <article class="share-article">
    <header class="share-header">
      <div class="share-header-row">
        <div>
          <p class="share-kicker">{{ kind === 'turn' ? '一问一答' : '对话全文' }}</p>
          <h1>{{ title }}</h1>
        </div>
        <slot name="header-extra"></slot>
      </div>
    </header>
    <section v-for="(m, i) in messages" :key="i" class="share-block" :class="m.role">
      <p class="share-label">{{ m.role === 'user' ? '问' : '答' }}</p>
      <div v-if="m.content" class="share-body md" v-html="renderMarkdown(m.content)"></div>
      <ul v-if="m.attachments && m.attachments.length" class="share-files">
        <li v-for="(a, j) in m.attachments" :key="j">{{ a.original_filename }}</li>
      </ul>
    </section>
    <footer class="share-foot">{{ footer }}</footer>
  </article>
</template>
```

- [ ] **Step 3: Slim `ShareView.vue`**

```vue
<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { fetchShare } from '../api.js'
import ShareArticle from '../components/ShareArticle.vue'

const route = useRoute()
const title = ref('')
const kind = ref('session')
const messages = ref([])
const error = ref('')
const loading = ref(true)

onMounted(async () => {
  try {
    const data = await fetchShare(route.params.token)
    title.value = data.title || '对话'
    kind.value = data.kind || 'session'
    messages.value = data.messages || []
  } catch (e) {
    error.value = e.message || '无法打开分享'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="share-page">
    <ShareArticle
      v-if="!loading && !error"
      :title="title"
      :kind="kind"
      :messages="messages"
      footer="只读分享"
    />
    <p v-else-if="loading" class="share-status">载入中…</p>
    <p v-else class="share-status">{{ error }}</p>
  </div>
</template>
```

Add CSS for the header row in `frontend/src/styles.css` after `.share-header`:

```css
.share-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}
```

- [ ] **Step 4: Regression**

Run: `cd frontend && npm test && npm run build`

Expected: tests PASS；build 成功

- [ ] **Step 5: Skip commit**（用户未要求）

---

### Task 6: `OwnerTurnView` 与路由 `/r/:sessionId/:messageId`

**Files:**
- Create: `frontend/src/views/OwnerTurnView.vue`
- Modify: `frontend/src/main.js`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `fetchTurn`、`shareTurn`、`copySharePath`、`ShareArticle`
- Produces: 登录只读页；页脚「只读预览」；标题旁「生成分享链接」；404 文案「这一轮不存在」；生成成功 `alert('分享链接已复制')` 且不 `router.push`

- [ ] **Step 1: Add the view**

Create `frontend/src/views/OwnerTurnView.vue`:

```vue
<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { fetchTurn, shareTurn } from '../api.js'
import ShareArticle from '../components/ShareArticle.vue'
import { copySharePath } from '../shareLink.js'

const route = useRoute()
const title = ref('')
const kind = ref('turn')
const messages = ref([])
const userMessageId = ref(null)
const error = ref('')
const loading = ref(true)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchTurn(route.params.sessionId, route.params.messageId)
    title.value = data.title || '对话'
    kind.value = data.kind || 'turn'
    messages.value = data.messages || []
    userMessageId.value = data.user_message_id ?? null
  } catch (e) {
    error.value = e.message || '这一轮不存在'
    messages.value = []
    userMessageId.value = null
  } finally {
    loading.value = false
  }
}

async function onShare() {
  if (userMessageId.value == null) {
    alert('找不到对应的问题，无法分享')
    return
  }
  try {
    const result = await shareTurn(route.params.sessionId, userMessageId.value)
    await copySharePath(result.path)
    alert('分享链接已复制')
  } catch (e) {
    alert(e.message || '生成分享链接失败')
  }
}

watch(
  () => [route.params.sessionId, route.params.messageId],
  () => {
    load().catch(() => {})
  },
  { immediate: true },
)
</script>

<template>
  <div class="share-page">
    <ShareArticle
      v-if="!loading && !error"
      :title="title"
      :kind="kind"
      :messages="messages"
      footer="只读预览"
    >
      <template #header-extra>
        <button type="button" class="share-make-link" @click="onShare">生成分享链接</button>
      </template>
    </ShareArticle>
    <p v-else-if="loading" class="share-status">载入中…</p>
    <p v-else class="share-status">{{ error }}</p>
  </div>
</template>
```

- [ ] **Step 2: Register the route**

In `frontend/src/main.js`:

```javascript
import OwnerTurnView from './views/OwnerTurnView.vue'
```

In `routes` array, next to `/s/:token`:

```javascript
    { path: '/r/:sessionId/:messageId', component: OwnerTurnView },
    { path: '/s/:token', component: ShareView },
```

- [ ] **Step 3: Button styles**

Add after `.share-header-row` in `frontend/src/styles.css`:

```css
.share-make-link {
  flex-shrink: 0;
  margin-top: 0.15rem;
  padding: 0;
  border: 0;
  background: transparent;
  font: inherit;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  color: var(--muted);
  cursor: pointer;
  white-space: nowrap;
}

.share-make-link:hover {
  color: var(--pine);
}
```

- [ ] **Step 4: Regression**

Run: `cd frontend && npm test && npm run build`

Expected: PASS；build 成功

- [ ] **Step 5: Skip commit**（用户未要求）

---

### Task 7: 搜索卡片链到 `/r/...`

**Files:**
- Modify: `frontend/src/views/SearchView.vue`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `turnPath(hit.session_id, hit.id)`
- Produces: 卡片主体为 `<RouterLink :to="turnPath(...)">`；展开按钮在链接外，只 `toggle`，不导航

- [ ] **Step 1: Wire the link**

In `SearchView.vue` script add:

```javascript
import { RouterLink } from 'vue-router'
import { turnPath } from '../turnPath.js'
```

Replace the `<li v-for ... class="hit-card">` inner content so the card chrome stays on `<li>`，链接包住 head/body/preview，`more-btn` 留在 `li` 里、链接外：

```html
        <li v-for="(hit, i) in hits" :key="hit.id" class="hit-card" :style="{ '--i': i }">
          <RouterLink class="hit-link" :to="turnPath(hit.session_id, hit.id)">
            <div class="hit-head">
              <span class="hit-role" :class="hit.role">{{ hit.role === 'user' ? '问' : '答' }}</span>
              <span class="hit-title" :title="hit.session_title || '未命名对话'">{{ hit.session_title || '未命名对话' }}</span>
              <span class="hit-time">{{ formatTime(hit.created_at) }}</span>
            </div>
            <div v-if="isOpen(hit.id)" class="hit-body md" v-html="renderMarkdown(hit.content)"></div>
            <p v-else class="hit-preview">{{ previewText(hit.content).text }}</p>
          </RouterLink>
          <button
            v-if="previewText(hit.content).more || isOpen(hit.id)"
            type="button"
            class="more-btn"
            :class="{ open: isOpen(hit.id) }"
            :aria-label="isOpen(hit.id) ? '收起' : '展开全文'"
            :title="isOpen(hit.id) ? '收起' : '展开全文'"
            @click.stop="toggle(hit.id)"
          >
            <Icon name="more" />
          </button>
        </li>
```

- [ ] **Step 2: Link styles**

After `.hit-card` in `frontend/src/styles.css`:

```css
.hit-link {
  display: block;
  color: inherit;
  text-decoration: none;
}

.hit-card:hover {
  border-color: rgba(36, 85, 68, 0.28);
}
```

- [ ] **Step 3: Confirm `turnPath` contract still holds**

Run: `cd frontend && npm test -- src/turnPath.test.js`

Expected: PASS（`turnPath(3, 9) === '/r/3/9'`）

- [ ] **Step 4: Full regression**

Run:

```
cd backend && PYTHONPATH=. pytest tests/test_turns.py tests/test_shares.py -v
cd frontend && npm test && npm run build
```

Expected: 全部 PASS；build 成功

- [ ] **Step 5: Skip commit**（用户未要求）

---

## Spec coverage

| Spec | Task |
|------|------|
| 点命中 → `/r/{sessionId}/{messageId}`，只展示这一问一答 | 6, 7 |
| 打开不写 `shares` | 2 |
| 「生成分享链接」才 `shareTurn`，复制、不跳走 | 6 |
| messageId 可以是问或答 | 1, 2 |
| 不改搜索 API / 不接 `hitMessageId` | （未改那些文件） |
| `GET .../turns/...` 形状与 404/401 | 2 |
| `find_turn` 共用给公开 turn 分享 | 1, 3 |
| `ShareArticle` + `ShareView` 页脚「只读分享」 | 5 |
| `OwnerTurnView` 页脚「只读预览」 | 6 |
| `fetchTurn` + 卡片 `to` | 4, 7 |
| 展开不导航 | 7 |
| 无答只有问 | 1, 2, 3 |
