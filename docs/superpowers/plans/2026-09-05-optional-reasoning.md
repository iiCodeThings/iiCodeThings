# Optional Reasoning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 输入框「推理」默认关闭；关闭时上游收到 `enable_thinking: false` 并忽略推理增量，打开时与现在一样展示并入库。

**Architecture:** `parse_enable_thinking` 解析 multipart；`stream_chat_completion` / `chat_completion` 在 JSON 根上带 `enable_thinking`。`_generate` 关闭时丢掉 reasoning 事件。Composer 勾选随发送传到 `sendMessage`。

**Tech Stack:** FastAPI、httpx、pytest、Vue 3、Vitest。

## Global Constraints

- 默认不开启推理；缺省或无法解析 → `false`；`"true"` / `"1"` / `"on"` → `true`。
- 上游 JSON 字段名 `enable_thinking`，与 `model`、`messages`、`stream` 并列。
- 关闭时不发 reasoning SSE、不入库 `messages.reasoning`（即使上游仍推 reasoning）。
- 打开时行为与现在相同。
- 勾选在本页停留期间保持，刷新后回到关；发送不重置勾选。
- `chat_completion`（重建标题）始终 `enable_thinking: false`。
- 不写 localStorage，不按模型存默认，不兼容多套字段名。
- 规范：`docs/superpowers/specs/2026-09-05-optional-reasoning-design.md`。
- 走 TDD。用户未要求时不要 `git commit`。

---

## File Structure

```
backend/app/services/llm.py
backend/app/routers/messages.py
backend/tests/test_llm.py
backend/tests/test_messages_send.py
frontend/src/api.js
frontend/src/components/Composer.vue
frontend/src/components/MessagePane.vue
frontend/src/components/AppShell.vue
frontend/src/styles.css
```

---

### Task 1: enable_thinking 进入上游 payload

**Files:**
- Modify: `backend/app/services/llm.py`
- Modify: `backend/tests/test_llm.py`

**Interfaces:**
- Consumes: 现有 `stream_chat_completion`、`chat_completion`
- Produces:
  - `parse_enable_thinking(raw) -> bool`
  - `stream_chat_completion(..., enable_thinking: bool = False)`
  - `chat_completion` 请求体始终含 `enable_thinking: False`（可用参数默认 False）

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_llm.py`:

```python
from app.services.llm import parse_enable_thinking


def test_parse_enable_thinking():
    assert parse_enable_thinking(None) is False
    assert parse_enable_thinking("") is False
    assert parse_enable_thinking("false") is False
    assert parse_enable_thinking("true") is True
    assert parse_enable_thinking("1") is True
    assert parse_enable_thinking("on") is True
    assert parse_enable_thinking("TRUE") is True
```

In `test_stream_chat_completion_reasoning_delta_done` handler, after existing asserts:

```python
        body = json.loads(request.content.decode("utf-8"))
        assert body["enable_thinking"] is False
```

In `test_chat_completion_reads_message_content` handler:

```python
        assert body["enable_thinking"] is False
```

Add:

```python
@pytest.mark.asyncio
async def test_stream_chat_completion_can_enable_thinking():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        assert body["enable_thinking"] is True
        return httpx.Response(
            200,
            content=b'data: {"choices":[{"delta":{"content":"hi"}}]}\n\ndata: [DONE]\n',
            headers={"Content-Type": "text/event-stream"},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        events = [
            event
            async for event in stream_chat_completion(
                base_url="https://api.example.com/v1",
                api_key="test-key",
                model="gpt-test",
                messages=[{"role": "user", "content": "hello"}],
                enable_thinking=True,
                client=client,
            )
        ]
    assert any(e.kind == "delta" for e in events)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_llm.py -v`

Expected: FAIL `cannot import name 'parse_enable_thinking'` 或 `enable_thinking` KeyError。

- [ ] **Step 3: Write minimal implementation**

In `backend/app/services/llm.py`:

```python
def parse_enable_thinking(raw) -> bool:
    if raw is None:
        return False
    return str(raw).strip().lower() in {"true", "1", "on"}
```

Add `enable_thinking: bool = False` to both `stream_chat_completion` and `chat_completion`. Put it in payload:

```python
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,  # or False in chat_completion
        "enable_thinking": enable_thinking,
    }
```

`chat_completion` always uses the parameter (default False). Do not add other thinking field names.

- [ ] **Step 4: Run tests and make sure they pass**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_llm.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

Skip unless the user asked to commit.

---

### Task 2: 发送消息尊重 enable_thinking 并丢掉关闭时的 reasoning

**Files:**
- Modify: `backend/app/routers/messages.py`
- Modify: `backend/tests/test_messages_send.py`

**Interfaces:**
- Consumes: `parse_enable_thinking`、`stream_chat_completion(..., enable_thinking=)`
- Produces: `_generate(..., enable_thinking: bool)`；multipart `enable_thinking`

关闭时：`ev.kind == "reasoning"` 则 `continue`（不累加、不 `_sse`）。打开时与现在相同。

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_messages_send.py`:

```python
def test_send_defaults_enable_thinking_false(client, db, settings, monkeypatch):
    seen = {}

    async def fake_stream(**kwargs):
        seen.update(kwargs)
        yield StreamEvent(kind="reasoning", text="secret")
        yield StreamEvent(kind="delta", text="ans")
        yield StreamEvent(kind="done")

    monkeypatch.setattr("app.routers.messages.stream_chat_completion", fake_stream)
    _login(client, db, settings)
    session_id = client.post("/api/sessions").json()["id"]
    model = LlmModel(
        name="Display",
        base_url="https://example.com/v1",
        api_key="sk-test",
        model="api-id",
        supports_vision=False,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    r = client.post(
        f"/api/sessions/{session_id}/messages",
        data={"content": "hi", "model_id": str(model.id)},
    )
    assert r.status_code == 200
    assert seen.get("enable_thinking") is False
    assert "event: reasoning" not in r.text
    db.expire_all()
    asst = db.query(Message).filter(Message.role == "assistant").one()
    assert asst.reasoning is None
    assert asst.content == "ans"


def test_send_enable_thinking_true_persists_reasoning(client, db, settings, monkeypatch):
    seen = {}

    async def fake_stream(**kwargs):
        seen.update(kwargs)
        yield StreamEvent(kind="reasoning", text="think")
        yield StreamEvent(kind="delta", text="ans")
        yield StreamEvent(kind="done")

    monkeypatch.setattr("app.routers.messages.stream_chat_completion", fake_stream)
    _login(client, db, settings)
    session_id = client.post("/api/sessions").json()["id"]
    model = LlmModel(
        name="Display",
        base_url="https://example.com/v1",
        api_key="sk-test",
        model="api-id",
        supports_vision=False,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    r = client.post(
        f"/api/sessions/{session_id}/messages",
        data={"content": "hi", "model_id": str(model.id), "enable_thinking": "true"},
    )
    assert r.status_code == 200
    assert seen.get("enable_thinking") is True
    assert "event: reasoning" in r.text
    db.expire_all()
    asst = db.query(Message).filter(Message.role == "assistant").one()
    assert asst.reasoning == "think"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_messages_send.py -v`

Expected: FAIL `enable_thinking` not passed or reasoning still stored.

- [ ] **Step 3: Write minimal implementation**

In `send_message`, after reading form:

```python
    from app.services.llm import parse_enable_thinking, stream_chat_completion
```

(`stream_chat_completion` already imported; add `parse_enable_thinking`.)

```python
    enable_thinking = parse_enable_thinking(form.get("enable_thinking"))
```

Pass into `_generate(..., enable_thinking)`.

`_generate` signature add `enable_thinking: bool`. Call:

```python
            async for ev in stream_chat_completion(
                base_url=model_row.base_url,
                api_key=model_row.api_key,
                model=model_row.model,
                messages=openai_msgs,
                enable_thinking=enable_thinking,
            ):
```

In the event loop, before handling reasoning:

```python
                if ev.kind == "reasoning":
                    if not enable_thinking:
                        continue
                    reasoning_acc += ev.text
                    yield _sse("reasoning", {"text": ev.text})
```

- [ ] **Step 4: Run tests and make sure they pass**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_messages_send.py tests/test_llm.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

Skip unless the user asked to commit.

---

### Task 3: 输入框「推理」勾选并传到发送

**Files:**
- Modify: `frontend/src/api.js`
- Modify: `frontend/src/components/Composer.vue`
- Modify: `frontend/src/components/MessagePane.vue`
- Modify: `frontend/src/components/AppShell.vue`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: multipart `enable_thinking`
- Produces: Composer emit `{ content, files, enableThinking }`；`sendMessage({ enableThinking })` 写入 `fd.append('enable_thinking', enableThinking ? 'true' : 'false')`

前端不强制新组件测试。跑现有 `npm test`。

- [ ] **Step 1: Composer**

```javascript
const enableThinking = ref(false)
```

`onSend` emit 加上 `enableThinking: enableThinking.value`。不要在发送后把勾选设回 false。

Template，附件和发送之间：

```html
        <label class="think-toggle">
          <input v-model="enableThinking" type="checkbox" name="enable_thinking" />
          推理
        </label>
```

`composer-actions` 布局：左侧附件 + 勾选，右侧发送。例如外包一层：

```html
      <div class="composer-actions">
        <div class="composer-actions-left">
          <label class="icon-btn attach">...</label>
          <label class="think-toggle">...</label>
        </div>
        <button type="button" class="send-btn" @click="onSend">发送</button>
      </div>
```

CSS：

```css
.composer-actions-left {
  display: flex;
  align-items: center;
  gap: 0.55rem;
}

.think-toggle {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.82rem;
  color: var(--ink-soft);
  cursor: pointer;
  user-select: none;
}
```

- [ ] **Step 2: Wire send**

`AppShell.vue` `onComposerSend({ content, files, enableThinking })` 把 `enableThinking` 传入 `viewRef.value?.send({ ..., enableThinking })`。

`MessagePane.vue` `send({ content, files, modelId, enableThinking })` 传给 `sendMessage({ ..., enableThinking: !!enableThinking })`。

`api.js` `sendMessage`：

```javascript
  fd.append('enable_thinking', enableThinking ? 'true' : 'false')
```

Default `enableThinking` to `false` if omitted.

- [ ] **Step 3: Run frontend tests**

Run: `cd frontend && npm test`

Expected: 现有测试 PASS。

- [ ] **Step 4: Commit**

Skip unless the user asked to commit.

---

## Self-Review

**Spec coverage:** parse + payload → Task 1；关推理丢 SSE/入库 → Task 2；勾选与粘滞 → Task 3；标题重建 → Task 1 `chat_completion` 默认 false。

**Placeholder scan:** 无 TBD。

**Type consistency:** `enable_thinking` / `enableThinking` / `parse_enable_thinking` 前后一致。
