# Pin Sessions and Composer Shortcuts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 导航栏可置顶多个会话（再置顶则顶到最前），输入框 Enter 换行、Ctrl+Enter / Shift+Enter 发送。

**Architecture:** `sessions.pinned_at` 可空时间戳；列表先按是否置顶再按 `pinned_at`/`updated_at` 排序。`POST`/`DELETE /api/sessions/{id}/pin` 只改 `pinned_at`、不改 `updated_at`。前端列表两个按钮；Composer 用纯函数判断按键后调用现有 `onSend`。

**Tech Stack:** FastAPI、SQLAlchemy 2、pytest、Vue 3、Vitest。

## Global Constraints

- 每个会话在列表只出现一次；再点置顶 = 挪到置顶区最前。
- 未置顶只显示「置顶」；已置顶显示「置顶」和「取消置顶」。
- `pinned_at` NULL = 未置顶；migrate 补列，方式同 `deleted_at`。
- GET 排序：置顶在前且 `pinned_at` 新→旧，其余 `updated_at` 新→旧；响应含 `pinned: bool`。
- POST pin / DELETE pin 不改 `updated_at`；软删除 404；DELETE 未置顶也 200。
- Enter 换行；Ctrl+Enter 或 Shift+Enter 发送；输入法组字不发送；不绑定 Command+Enter。
- 不做拖拽、不写 localStorage、不改搜索页。
- 规范：`docs/superpowers/specs/2026-09-04-pin-and-composer-keys-design.md`。
- 走 TDD。用户未要求时不要 `git commit`（计划里的 Commit 步骤跳过即可）。

---

## File Structure

```
backend/app/tables.py              # ChatSession.pinned_at
backend/app/db.py                  # migrate_schema 补 pinned_at
backend/app/routers/sessions.py    # _out.pinned、列表排序、pin 路由
backend/tests/test_sessions_api.py # CRUD 断言 pinned: false
backend/tests/test_pin_api.py      # 置顶行为
frontend/src/api.js
frontend/src/components/Icons.vue    # pin / unpin 图标
frontend/src/components/AppShell.vue
frontend/src/styles.css
frontend/src/composerKeys.js
frontend/src/composerKeys.test.js
frontend/src/components/Composer.vue
```

---

### Task 1: pinned_at 列、列表排序、_out.pinned

**Files:**
- Modify: `backend/app/tables.py`
- Modify: `backend/app/db.py`
- Modify: `backend/app/routers/sessions.py`
- Modify: `backend/tests/test_sessions_api.py`
- Create: `backend/tests/test_pin_api.py`（本任务先写列表/缺省字段；Task 2 补 pin 路由测试）

**Interfaces:**
- Consumes: 现有 `ChatSession`、`_out`、`list_sessions`
- Produces: `ChatSession.pinned_at: datetime | None`；`_out` 增加 `"pinned": row.pinned_at is not None`；`list_sessions` 排序 `pinned_at.is_(None), pinned_at.desc(), updated_at.desc()`

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_sessions_api.py`, after create assert add:

```python
    assert body["pinned"] is False
```

Create `backend/tests/test_pin_api.py` with login helper copied from `test_sessions_api.py` and:

```python
from datetime import datetime, timedelta

from app.db import seed_default_user
from app.security import hash_password
from app.tables import ChatSession


def _login(client, db, settings):
    seed_default_user(db, settings.app_username, hash_password(settings.app_password))
    client.post("/api/auth/login", json={"username": "admin", "password": "passpass"})


def test_list_orders_pinned_first_then_updated_at(client, db, settings):
    _login(client, db, settings)
    older = client.post("/api/sessions").json()["id"]
    newer = client.post("/api/sessions").json()["id"]
    pinned = client.post("/api/sessions").json()["id"]
    db.expire_all()
    t0 = datetime.utcnow() - timedelta(days=2)
    t1 = datetime.utcnow() - timedelta(days=1)
    tpin = datetime.utcnow()
    db.query(ChatSession).filter(ChatSession.id == older).update(
        {"updated_at": t0, "title": "旧"}
    )
    db.query(ChatSession).filter(ChatSession.id == newer).update(
        {"updated_at": t1, "title": "新"}
    )
    db.query(ChatSession).filter(ChatSession.id == pinned).update(
        {"updated_at": t0, "pinned_at": tpin, "title": "钉"}
    )
    db.commit()
    ids = [s["id"] for s in client.get("/api/sessions").json()]
    assert ids[0] == pinned
    assert ids[1] == newer
    assert ids[2] == older
    flags = {s["id"]: s["pinned"] for s in client.get("/api/sessions").json()}
    assert flags[pinned] is True
    assert flags[newer] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_sessions_api.py tests/test_pin_api.py -v`

Expected: FAIL `pinned` KeyError 或列不存在。

- [ ] **Step 3: Write minimal implementation**

`backend/app/tables.py` on `ChatSession` after `deleted_at`:

```python
    pinned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

`backend/app/db.py` `migrate_schema` after `deleted_at` block:

```python
    if "pinned_at" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE sessions ADD COLUMN pinned_at DATETIME"))
```

`backend/app/routers/sessions.py`:

`_out` add `"pinned": row.pinned_at is not None`.

`list_sessions` order_by:

```python
        .order_by(
            ChatSession.pinned_at.is_(None),
            ChatSession.pinned_at.desc(),
            ChatSession.updated_at.desc(),
        )
```

- [ ] **Step 4: Run tests and make sure they pass**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_sessions_api.py tests/test_pin_api.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

Skip unless the user asked to commit.

---

### Task 2: POST/DELETE /api/sessions/{id}/pin

**Files:**
- Modify: `backend/app/routers/sessions.py`
- Modify: `backend/tests/test_pin_api.py`

**Interfaces:**
- Consumes: `get_live_session`、`_out`
- Produces: `POST /api/sessions/{session_id}/pin`；`DELETE /api/sessions/{session_id}/pin`

写库辅助（与 retitle 相同，显式保留 `updated_at`）：

```python
def _write_pin(db: Session, row: ChatSession, pinned_at: datetime | None) -> ChatSession:
    old_updated = row.updated_at
    db.query(ChatSession).filter(ChatSession.id == row.id).update(
        {"pinned_at": pinned_at, "updated_at": old_updated},
        synchronize_session="fetch",
    )
    db.commit()
    db.refresh(row)
    return row
```

POST：`pinned_at=datetime.utcnow()`。DELETE：`pinned_at=None`。不存在或软删除 → 404 `会话不存在`。

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_pin_api.py`:

```python
def test_pin_unauthenticated(client):
    r = client.post("/api/sessions/1/pin")
    assert r.status_code == 401


def test_pin_deleted_404(client, db, settings):
    _login(client, db, settings)
    session_id = client.post("/api/sessions").json()["id"]
    client.delete(f"/api/sessions/{session_id}")
    r = client.post(f"/api/sessions/{session_id}/pin")
    assert r.status_code == 404
    assert r.json()["detail"] == "会话不存在"
    r = client.delete(f"/api/sessions/{session_id}/pin")
    assert r.status_code == 404


def test_pin_bump_order_keeps_updated_at(client, db, settings):
    _login(client, db, settings)
    a = client.post("/api/sessions").json()["id"]
    b = client.post("/api/sessions").json()["id"]
    db.expire_all()
    old_a = datetime.utcnow() - timedelta(days=5)
    db.query(ChatSession).filter(ChatSession.id == a).update({"updated_at": old_a})
    db.query(ChatSession).filter(ChatSession.id == b).update({"updated_at": old_a})
    db.commit()
    assert client.post(f"/api/sessions/{a}/pin").status_code == 200
    assert client.post(f"/api/sessions/{b}/pin").json()["pinned"] is True
    ids = [s["id"] for s in client.get("/api/sessions").json()]
    assert ids[:2] == [b, a]
    r = client.post(f"/api/sessions/{a}/pin")
    assert r.status_code == 200
    ids = [s["id"] for s in client.get("/api/sessions").json()]
    assert ids[0] == a
    db.expire_all()
    row = db.get(ChatSession, a)
    assert abs((row.updated_at - old_a).total_seconds()) < 2


def test_unpin_returns_to_updated_order(client, db, settings):
    _login(client, db, settings)
    a = client.post("/api/sessions").json()["id"]
    b = client.post("/api/sessions").json()["id"]
    client.post(f"/api/sessions/{a}/pin")
    r = client.delete(f"/api/sessions/{a}/pin")
    assert r.status_code == 200
    assert r.json()["pinned"] is False
    r = client.delete(f"/api/sessions/{a}/pin")
    assert r.status_code == 200
    ids = [s["id"] for s in client.get("/api/sessions").json()]
    assert a in ids and b in ids
    assert ids.index(b) < ids.index(a)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_pin_api.py -v`

Expected: FAIL 404 on `POST .../pin`.

- [ ] **Step 3: Write minimal implementation**

In `backend/app/routers/sessions.py` add `_write_pin` and:

```python
@router.post("/{session_id}/pin")
def pin_session(
    session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    row = get_live_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return _out(_write_pin(db, row, datetime.utcnow()))


@router.delete("/{session_id}/pin")
def unpin_session(
    session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    row = get_live_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return _out(_write_pin(db, row, None))
```

`datetime` 已在 `sessions.py` 导入。

- [ ] **Step 4: Run tests and make sure they pass**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_pin_api.py tests/test_sessions_api.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

Skip unless the user asked to commit.

---

### Task 3: 导航栏置顶按钮

**Files:**
- Modify: `frontend/src/api.js`
- Modify: `frontend/src/components/Icons.vue`
- Modify: `frontend/src/components/AppShell.vue`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `POST/DELETE /api/sessions/{id}/pin`、列表项 `pinned`
- Produces: `pinSession(id)`、`unpinSession(id)`

前端不强制组件测试。

- [ ] **Step 1: API helpers**

After `deleteSession` in `frontend/src/api.js`:

```javascript
export async function pinSession(id) {
  const res = await jsonFetch(`/api/sessions/${id}/pin`, { method: 'POST' })
  if (!res.ok) throw new Error('置顶失败')
  return res.json()
}

export async function unpinSession(id) {
  const res = await jsonFetch(`/api/sessions/${id}/pin`, { method: 'DELETE' })
  if (!res.ok) throw new Error('取消置顶失败')
  return res.json()
}
```

- [ ] **Step 2: Icons**

In `frontend/src/components/Icons.vue`, add two stroke-only 24×24 icons matching existing pine/ink style:

- `name === 'pin'`：简易图钉（竖针 + 圆头）
- `name === 'unpin'`：同样图钉加一小斜线（表示取消）

- [ ] **Step 3: AppShell**

Import `pinSession`、`unpinSession`。

```javascript
async function onPin(s, ev) {
  ev.stopPropagation()
  await pinSession(s.id)
  await loadSessions()
}

async function onUnpin(s, ev) {
  ev.stopPropagation()
  await unpinSession(s.id)
  await loadSessions()
}
```

List item: `:class="{ active: currentId === s.id, pinned: s.pinned }"`。

Actions，放在重命名之前：

```html
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
```

- [ ] **Step 4: CSS**

```css
.session-list li.pinned {
  background: rgba(255, 253, 248, 0.55);
}

.session-list li.pinned .session-title::before {
  content: "◉ ";
  color: var(--pine);
  font-size: 0.65rem;
}
```

- [ ] **Step 5: Run frontend tests**

Run: `cd frontend && npm test`

Expected: 现有测试 PASS。

- [ ] **Step 6: Commit**

Skip unless the user asked to commit.

---

### Task 4: Composer 快捷键

**Files:**
- Create: `frontend/src/composerKeys.js`
- Create: `frontend/src/composerKeys.test.js`
- Modify: `frontend/src/components/Composer.vue`

**Interfaces:**
- Consumes: textarea `keydown`
- Produces: `shouldSendOnKeydown(event) -> boolean`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/composerKeys.test.js`:

```javascript
import { describe, expect, it } from 'vitest'
import { shouldSendOnKeydown } from './composerKeys.js'

function ev(partial) {
  return {
    key: 'Enter',
    ctrlKey: false,
    shiftKey: false,
    metaKey: false,
    isComposing: false,
    keyCode: 13,
    ...partial,
  }
}

describe('shouldSendOnKeydown', () => {
  it('does not send on plain Enter', () => {
    expect(shouldSendOnKeydown(ev())).toBe(false)
  })
  it('sends on Ctrl+Enter', () => {
    expect(shouldSendOnKeydown(ev({ ctrlKey: true }))).toBe(true)
  })
  it('sends on Shift+Enter', () => {
    expect(shouldSendOnKeydown(ev({ shiftKey: true }))).toBe(true)
  })
  it('does not send on Command+Enter', () => {
    expect(shouldSendOnKeydown(ev({ metaKey: true }))).toBe(false)
  })
  it('does not send while composing', () => {
    expect(shouldSendOnKeydown(ev({ ctrlKey: true, isComposing: true }))).toBe(false)
    expect(shouldSendOnKeydown(ev({ ctrlKey: true, keyCode: 229 }))).toBe(false)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/composerKeys.test.js`

Expected: FAIL cannot find module `composerKeys.js`.

- [ ] **Step 3: Write minimal implementation**

`frontend/src/composerKeys.js`:

```javascript
export function shouldSendOnKeydown(event) {
  if (event.isComposing || event.keyCode === 229) return false
  if (event.key !== 'Enter') return false
  return Boolean(event.ctrlKey || event.shiftKey)
}
```

`Composer.vue`: import `shouldSendOnKeydown`。

```javascript
function onKeydown(e) {
  if (!shouldSendOnKeydown(e)) return
  e.preventDefault()
  onSend()
}
```

Textarea: `@keydown="onKeydown"`。

- [ ] **Step 4: Run tests and make sure they pass**

Run: `cd frontend && npm test`

Expected: 全部 PASS（含新 5 项）。

- [ ] **Step 5: Commit**

Skip unless the user asked to commit.

---

## Self-Review

**Spec coverage:** 置顶列/排序/pinned 字段 → Task 1；POST/DELETE pin 与 updated_at → Task 2；两按钮与标记 → Task 3；快捷键与输入法 → Task 4。

**Placeholder scan:** 无 TBD。

**Type consistency:** `pinned_at`、`pinned` bool、`pinSession`/`unpinSession`、`shouldSendOnKeydown` 前后一致。
