# Rebuild Session Titles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在设置页选一个模型、点一次按钮，串行为每个未删除 session 调用大模型生成言简意赅的标题并写回 `sessions.title`。

**Architecture:** 纯函数整理转写与清洗标题；`chat_completion` 做非流式 OpenAI 兼容调用；`generate_session_title` 在超长时丢掉最早轮次重试；`POST /api/sessions/{id}/retitle` 写库且不改 `updated_at`。设置页串行调用该接口并刷新左栏列表。

**Tech Stack:** FastAPI、SQLAlchemy 2、httpx、pytest、Vue 3。

## Global Constraints

- 单用户，需登录 Cookie `chat_session`。
- 只对接 OpenAI 兼容 `chat.completions`；本功能用 `stream: false`。
- 不把历史 `reasoning` 或图片送给模型；文档用 `extracted_text`。
- 覆盖全部 live session 标题（含手动改过的）；软删除的不处理。
- 无消息 → 跳过、不调模型。
- 某个 session 失败不影响后续；前端汇总成功 / 跳过 / 失败。
- 只改 `title`（最多 128 字符），不改 `updated_at`。
- 规范：`docs/superpowers/specs/2026-09-04-rebuild-session-titles-design.md`。
- 实现时走 TDD：先写失败测试，再写最小实现。用户未要求时不要 `git commit`（计划里的 Commit 步骤跳过即可）。

---

## File Structure

```
backend/app/title.py                 # 增加清洗、转写、system prompt
backend/app/services/llm.py          # 增加 chat_completion()
backend/app/services/retitle.py      # generate_session_title()
backend/app/routers/sessions.py      # POST /{session_id}/retitle
backend/tests/test_title.py
backend/tests/test_llm.py
backend/tests/test_retitle.py
backend/tests/test_retitle_api.py
frontend/src/api.js
frontend/src/views/SettingsView.vue
frontend/src/components/AppShell.vue
frontend/src/styles.css
```

---

### Task 1: 标题清洗与对话转写

**Files:**
- Modify: `backend/app/title.py`
- Modify: `backend/tests/test_title.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `TITLE_SYSTEM_PROMPT: str`
  - `clean_generated_title(text: str, max_len: int = 128) -> str`
  - `turns_from_messages(items: list[dict]) -> list[dict]`（每项 `{role, content, attachments: []}`）
  - `format_title_user_content(turns: list[dict]) -> str`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_title.py`:

```python
from app.title import (
    TITLE_SYSTEM_PROMPT,
    clean_generated_title,
    format_title_user_content,
    turns_from_messages,
)


def test_clean_generated_title_strips_quotes_and_newlines():
    assert clean_generated_title('  「韦伯与正当性」\n ') == "韦伯与正当性"
    assert clean_generated_title('"Hello"') == "Hello"
    assert clean_generated_title("   ") == ""
    assert len(clean_generated_title("字" * 200)) == 128


def test_turns_from_messages_uses_doc_text_omits_reasoning_and_images():
    turns = turns_from_messages(
        [
            {
                "role": "user",
                "content": "看这个",
                "reasoning": "should-not-appear",
                "attachments": [
                    {"kind": "document", "extracted_text": "人类学笔记"},
                    {"kind": "image", "extracted_text": None, "storage_path": "/tmp/a.png"},
                ],
            },
            {
                "role": "assistant",
                "content": "好",
                "reasoning": "internal",
                "attachments": [],
            },
        ]
    )
    blob = format_title_user_content(turns)
    assert TITLE_SYSTEM_PROMPT
    assert blob == "用户：看这个\n人类学笔记\n助手：好"
    assert "internal" not in blob
    assert "should-not-appear" not in blob
    assert "/tmp/a.png" not in blob
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_title.py -v`

Expected: FAIL `cannot import name 'clean_generated_title'`

- [ ] **Step 3: Write minimal implementation**

Append to `backend/app/title.py` (keep existing `auto_title`):

```python
TITLE_SYSTEM_PROMPT = (
    "根据对话生成会话标题。言简意赅；与对话同一语言；"
    "不要引号、句号、不要「标题：」之类前缀；不要解释。"
)


def clean_generated_title(text: str, max_len: int = 128) -> str:
    raw = " ".join((text or "").split())
    quotes = "\"'“”‘’「」『』"
    raw = raw.strip(quotes + " \t")
    raw = " ".join(raw.split())
    return raw[:max_len]


def turns_from_messages(items: list[dict]) -> list[dict]:
    out: list[dict] = []
    for item in items:
        parts = [item.get("content") or ""]
        if item.get("role") == "user":
            for att in item.get("attachments") or []:
                if att.get("kind") == "document" and att.get("extracted_text"):
                    parts.append(att["extracted_text"])
        out.append(
            {
                "role": item["role"],
                "content": "\n".join(p for p in parts if p),
                "attachments": [],
            }
        )
    return out


def format_title_user_content(turns: list[dict]) -> str:
    labels = {"user": "用户：", "assistant": "助手："}
    lines = []
    for turn in turns:
        prefix = labels.get(turn["role"], f"{turn['role']}：")
        lines.append(f"{prefix}{turn.get('content') or ''}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests and make sure they pass**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_title.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

Skip unless the user asked to commit.

---

### Task 2: 非流式 chat_completion

**Files:**
- Modify: `backend/app/services/llm.py`
- Modify: `backend/tests/test_llm.py`

**Interfaces:**
- Consumes: `_join_url`
- Produces: `CompletionResult(ok: bool, text: str = "", error: str = "", status_code: int | None = None)`；`async def chat_completion(*, base_url: str, api_key: str, model: str, messages: list[dict], timeout: float = 120.0, client: httpx.AsyncClient | None = None) -> CompletionResult`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_llm.py`:

```python
from app.services.llm import chat_completion


@pytest.mark.asyncio
async def test_chat_completion_reads_message_content():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        assert body["stream"] is False
        assert body["model"] == "gpt-test"
        assert body["messages"][0]["role"] == "user"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "韦伯与正当性"}}]},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await chat_completion(
            base_url="https://api.example.com/v1",
            api_key="test-key",
            model="gpt-test",
            messages=[{"role": "user", "content": "hello"}],
            client=client,
        )
    assert result.ok is True
    assert result.text == "韦伯与正当性"


@pytest.mark.asyncio
async def test_chat_completion_non_200_is_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text='{"error":{"message":"context_length_exceeded"}}')

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await chat_completion(
            base_url="https://api.example.com/v1",
            api_key="test-key",
            model="gpt-test",
            messages=[{"role": "user", "content": "hello"}],
            client=client,
        )
    assert result.ok is False
    assert result.status_code == 400
    assert "context_length" in result.error
```

Add `import json` at the top of `test_llm.py` if missing.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_llm.py -v`

Expected: FAIL `cannot import name 'chat_completion'`

- [ ] **Step 3: Write minimal implementation**

Append to `backend/app/services/llm.py`:

```python
@dataclass
class CompletionResult:
    ok: bool
    text: str = ""
    error: str = ""
    status_code: int | None = None


async def chat_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    timeout: float = 120.0,
    client: httpx.AsyncClient | None = None,
) -> CompletionResult:
    own = client is None
    client = client or httpx.AsyncClient(timeout=timeout)
    url = _join_url(base_url, "/chat/completions")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "stream": False}
    try:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            return CompletionResult(
                ok=False,
                error=(resp.text or "")[:500],
                status_code=resp.status_code,
            )
        data = resp.json()
        text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        return CompletionResult(ok=True, text=text, status_code=resp.status_code)
    except httpx.TimeoutException:
        return CompletionResult(ok=False, error="上游请求超时")
    except httpx.RequestError as exc:
        return CompletionResult(ok=False, error=f"上游连接失败：{exc}")
    finally:
        if own:
            await client.aclose()
```

- [ ] **Step 4: Run tests and make sure they pass**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_llm.py -v`

Expected: PASS（含原有流式测试）

- [ ] **Step 5: Commit**

Skip unless the user asked to commit.

---

### Task 3: generate_session_title（超长重试）

**Files:**
- Create: `backend/app/services/retitle.py`
- Create: `backend/tests/test_retitle.py`

**Interfaces:**
- Consumes: `TITLE_SYSTEM_PROMPT`、`clean_generated_title`、`format_title_user_content`、`drop_oldest_turn`、`is_context_length_error`、`CompletionResult`、`chat_completion`
- Produces:
  - `class TitleGenerationError(Exception)`
  - `async def generate_session_title(*, base_url: str, api_key: str, model: str, turns: list[dict], chat_fn=chat_completion) -> str`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_retitle.py`:

```python
import pytest

from app.services.llm import CompletionResult
from app.services.retitle import TitleGenerationError, generate_session_title


@pytest.mark.asyncio
async def test_generate_session_title_returns_cleaned_text():
    async def fake_chat(**kwargs):
        assert kwargs["messages"][0]["role"] == "system"
        assert "用户：韦伯" in kwargs["messages"][1]["content"]
        return CompletionResult(ok=True, text='「正当性」\n')

    title = await generate_session_title(
        base_url="https://example.com/v1",
        api_key="sk",
        model="m",
        turns=[{"role": "user", "content": "韦伯", "attachments": []}],
        chat_fn=fake_chat,
    )
    assert title == "正当性"


@pytest.mark.asyncio
async def test_generate_session_title_retries_after_context_length():
    calls = []

    async def fake_chat(**kwargs):
        calls.append(kwargs["messages"][1]["content"])
        if len(calls) == 1:
            return CompletionResult(
                ok=False,
                error='{"error":{"message":"context_length_exceeded"}}',
                status_code=400,
            )
        return CompletionResult(ok=True, text="后一轮")

    title = await generate_session_title(
        base_url="https://example.com/v1",
        api_key="sk",
        model="m",
        turns=[
            {"role": "user", "content": "早", "attachments": []},
            {"role": "assistant", "content": "回", "attachments": []},
            {"role": "user", "content": "晚", "attachments": []},
        ],
        chat_fn=fake_chat,
    )
    assert title == "后一轮"
    assert "早" in calls[0]
    assert "早" not in calls[1]
    assert "晚" in calls[1]


@pytest.mark.asyncio
async def test_generate_session_title_empty_output_raises():
    async def fake_chat(**kwargs):
        return CompletionResult(ok=True, text="   ")

    with pytest.raises(TitleGenerationError):
        await generate_session_title(
            base_url="https://example.com/v1",
            api_key="sk",
            model="m",
            turns=[{"role": "user", "content": "x", "attachments": []}],
            chat_fn=fake_chat,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_retitle.py -v`

Expected: FAIL `ModuleNotFoundError: app.services.retitle`

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/services/retitle.py`:

```python
from __future__ import annotations

from app.services.context import drop_oldest_turn, is_context_length_error
from app.services.llm import CompletionResult, chat_completion
from app.title import TITLE_SYSTEM_PROMPT, clean_generated_title, format_title_user_content


class TitleGenerationError(Exception):
    pass


async def generate_session_title(
    *,
    base_url: str,
    api_key: str,
    model: str,
    turns: list[dict],
    chat_fn=chat_completion,
) -> str:
    items = [dict(t) for t in turns]
    while True:
        messages = [
            {"role": "system", "content": TITLE_SYSTEM_PROMPT},
            {"role": "user", "content": format_title_user_content(items)},
        ]
        result: CompletionResult = await chat_fn(
            base_url=base_url,
            api_key=api_key,
            model=model,
            messages=messages,
        )
        if not result.ok:
            if is_context_length_error(result.status_code or 0, result.error) and len(items) > 1:
                items = drop_oldest_turn(items)
                continue
            raise TitleGenerationError(result.error or "生成标题失败")
        cleaned = clean_generated_title(result.text)
        if not cleaned:
            raise TitleGenerationError("模型未返回标题")
        return cleaned
```

- [ ] **Step 4: Run tests and make sure they pass**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_retitle.py tests/test_title.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

Skip unless the user asked to commit.

---

### Task 4: POST /api/sessions/{id}/retitle

**Files:**
- Modify: `backend/app/routers/sessions.py`
- Create: `backend/tests/test_retitle_api.py`

**Interfaces:**
- Consumes: `get_live_session`、`LlmModel`、`Message`、`turns_from_messages`、`generate_session_title`、`TitleGenerationError`
- Produces: `POST /api/sessions/{session_id}/retitle` body `RetitleIn(model_id: int)`

行为（必须全部覆盖）：

- 未登录 401
- `model_id` 不存在 → 400 `请先在设置中添加模型`
- session 不存在或已软删除 → 404 `会话不存在`
- 无消息 → 200 `{"skipped": true, "reason": "no_messages"}`，不调用 `generate_session_title`，title 不变
- 成功 → 200 `{id, title, created_at, updated_at}`，title 为清洗后文本，`updated_at` 与调用前相同
- `TitleGenerationError` → 502，title 不变
- 发给 `generate_session_title` 的 turns 不含 reasoning（由 `turns_from_messages` 保证；本任务测 payload 通过 monkeypatch 捕获 turns）

写库时用 Query `update`，同时写入原来的 `updated_at`，避免 `onupdate=func.now()` 刷新时间：

```python
db.query(ChatSession).filter(ChatSession.id == row.id).update(
    {"title": title, "updated_at": old_updated},
    synchronize_session="fetch",
)
```

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_retitle_api.py`:

```python
from datetime import datetime, timedelta

from app.db import seed_default_user
from app.security import hash_password
from app.tables import Attachment, ChatSession, LlmModel, Message


def _login(client, db, settings):
    seed_default_user(db, settings.app_username, hash_password(settings.app_password))
    client.post("/api/auth/login", json={"username": "admin", "password": "passpass"})


def _model(db) -> LlmModel:
    row = LlmModel(
        name="Display",
        base_url="https://example.com/v1",
        api_key="sk-test",
        model="api-id",
        supports_vision=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_retitle_unauthenticated(client):
    r = client.post("/api/sessions/1/retitle", json={"model_id": 1})
    assert r.status_code == 401


def test_retitle_missing_model_400(client, db, settings):
    _login(client, db, settings)
    session_id = client.post("/api/sessions").json()["id"]
    r = client.post(f"/api/sessions/{session_id}/retitle", json={"model_id": 999})
    assert r.status_code == 400
    assert r.json()["detail"] == "请先在设置中添加模型"


def test_retitle_deleted_session_404(client, db, settings):
    _login(client, db, settings)
    model = _model(db)
    session_id = client.post("/api/sessions").json()["id"]
    client.delete(f"/api/sessions/{session_id}")
    r = client.post(f"/api/sessions/{session_id}/retitle", json={"model_id": model.id})
    assert r.status_code == 404
    assert r.json()["detail"] == "会话不存在"


def test_retitle_empty_session_skipped(client, db, settings, monkeypatch):
    called = {"n": 0}

    async def boom(**kwargs):
        called["n"] += 1
        raise AssertionError("should not call")

    monkeypatch.setattr("app.routers.sessions.generate_session_title", boom)
    _login(client, db, settings)
    model = _model(db)
    session_id = client.post("/api/sessions").json()["id"]
    r = client.post(f"/api/sessions/{session_id}/retitle", json={"model_id": model.id})
    assert r.status_code == 200
    assert r.json() == {"skipped": True, "reason": "no_messages"}
    assert called["n"] == 0
    db.expire_all()
    assert db.get(ChatSession, session_id).title == "新对话"


def test_retitle_success_keeps_updated_at(client, db, settings, monkeypatch):
    async def fake_generate(**kwargs):
        assert kwargs["turns"][0]["content"] == "韦伯"
        assert "internal" not in kwargs["turns"][0]["content"]
        return "韦伯与正当性"

    monkeypatch.setattr("app.routers.sessions.generate_session_title", fake_generate)
    _login(client, db, settings)
    model = _model(db)
    session_id = client.post("/api/sessions").json()["id"]
    db.expire_all()
    session = db.get(ChatSession, session_id)
    old_updated = datetime.utcnow() - timedelta(days=3)
    session.updated_at = old_updated
    session.title = "旧标题"
    db.add(
        Message(
            session_id=session_id,
            role="user",
            content="韦伯",
            reasoning="internal",
            model_name="Display",
            model="api-id",
        )
    )
    db.commit()
    r = client.post(f"/api/sessions/{session_id}/retitle", json={"model_id": model.id})
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "韦伯与正当性"
    db.expire_all()
    row = db.get(ChatSession, session_id)
    assert row.title == "韦伯与正当性"
    assert abs((row.updated_at - old_updated).total_seconds()) < 2


def test_retitle_omits_reasoning_includes_doc_not_image(client, db, settings, monkeypatch):
    captured = {}

    async def fake_generate(**kwargs):
        captured["turns"] = kwargs["turns"]
        return "笔记摘要"

    monkeypatch.setattr("app.routers.sessions.generate_session_title", fake_generate)
    _login(client, db, settings)
    model = _model(db)
    session_id = client.post("/api/sessions").json()["id"]
    msg = Message(
        session_id=session_id,
        role="user",
        content="看这个",
        reasoning="secret-reasoning",
        model_name="Display",
        model="api-id",
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    db.add(
        Attachment(
            message_id=msg.id,
            kind="document",
            original_filename="note.md",
            mime_type="text/markdown",
            storage_path="/tmp/note.md",
            extracted_text="人类学笔记",
        )
    )
    db.add(
        Attachment(
            message_id=msg.id,
            kind="image",
            original_filename="a.png",
            mime_type="image/png",
            storage_path="/tmp/a.png",
            extracted_text=None,
        )
    )
    db.commit()
    r = client.post(f"/api/sessions/{session_id}/retitle", json={"model_id": model.id})
    assert r.status_code == 200
    blob = captured["turns"][0]["content"]
    assert "人类学笔记" in blob
    assert "secret-reasoning" not in blob
    assert "/tmp/a.png" not in blob


def test_retitle_upstream_error_502(client, db, settings, monkeypatch):
    async def fake_generate(**kwargs):
        from app.services.retitle import TitleGenerationError

        raise TitleGenerationError("上游挂了")

    monkeypatch.setattr("app.routers.sessions.generate_session_title", fake_generate)
    _login(client, db, settings)
    model = _model(db)
    session_id = client.post("/api/sessions").json()["id"]
    db.add(
        Message(
            session_id=session_id,
            role="user",
            content="hi",
            model_name="Display",
            model="api-id",
        )
    )
    db.commit()
    r = client.post(f"/api/sessions/{session_id}/retitle", json={"model_id": model.id})
    assert r.status_code == 502
    assert r.json()["detail"] == "上游挂了"
    db.expire_all()
    assert db.get(ChatSession, session_id).title == "新对话"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_retitle_api.py -v`

Expected: FAIL 404 on `POST .../retitle`（路由不存在）

- [ ] **Step 3: Write minimal implementation**

In `backend/app/routers/sessions.py`:

- Import `selectinload`、`HTTPException`（已有）、`LlmModel`、`Message`、`turns_from_messages`、`generate_session_title`、`TitleGenerationError`。
- Add body model and route. Keep `_out` 用于成功响应。

```python
from sqlalchemy.orm import Session, selectinload

from app.services.retitle import TitleGenerationError, generate_session_title
from app.tables import ChatSession, LlmModel, Message, User
from app.title import turns_from_messages


class RetitleIn(BaseModel):
    model_id: int


@router.post("/{session_id}/retitle")
async def retitle_session(
    session_id: int,
    body: RetitleIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = get_live_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    model_row = db.get(LlmModel, body.model_id)
    if model_row is None:
        raise HTTPException(status_code=400, detail="请先在设置中添加模型")
    msgs = (
        db.query(Message)
        .options(selectinload(Message.attachments))
        .filter(Message.session_id == row.id)
        .order_by(Message.id.asc())
        .all()
    )
    if not msgs:
        return {"skipped": True, "reason": "no_messages"}
    items = [
        {
            "role": m.role,
            "content": m.content or "",
            "attachments": [
                {
                    "kind": a.kind,
                    "extracted_text": a.extracted_text,
                    "storage_path": a.storage_path,
                }
                for a in m.attachments
            ],
        }
        for m in msgs
    ]
    turns = turns_from_messages(items)
    try:
        title = await generate_session_title(
            base_url=model_row.base_url,
            api_key=model_row.api_key,
            model=model_row.model,
            turns=turns,
        )
    except TitleGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc) or "生成标题失败") from exc
    old_updated = row.updated_at
    db.query(ChatSession).filter(ChatSession.id == row.id).update(
        {"title": title[:128], "updated_at": old_updated},
        synchronize_session="fetch",
    )
    db.commit()
    db.refresh(row)
    return _out(row)
```

- [ ] **Step 4: Run tests and make sure they pass**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_retitle_api.py tests/test_sessions_api.py tests/test_retitle.py tests/test_title.py tests/test_llm.py -v`

Expected: PASS。若 `updated_at` 比较因 SQLite 微秒失败，放宽到 `< 2` 秒（测试里已写）。

- [ ] **Step 5: Commit**

Skip unless the user asked to commit.

---

### Task 5: 设置页按钮与串行调用

**Files:**
- Modify: `frontend/src/api.js`
- Modify: `frontend/src/views/SettingsView.vue`
- Modify: `frontend/src/components/AppShell.vue`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `listSessions`、`listModels`、`POST /api/sessions/{id}/retitle`
- Produces: `retitleSession(id, modelId)`；设置页事件 `retitled`；AppShell `@retitled="loadSessions"`

前端不强制组件测试（规格如此）。

- [ ] **Step 1: Add API helper**

In `frontend/src/api.js` after `deleteSession`:

```javascript
export async function retitleSession(id, modelId) {
  const res = await jsonFetch(`/api/sessions/${id}/retitle`, {
    method: 'POST',
    body: JSON.stringify({ model_id: modelId }),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : '重建标题失败')
  }
  return data
}
```

- [ ] **Step 2: Settings UI and loop**

`frontend/src/views/SettingsView.vue`:

- Import `listSessions`、`retitleSession`；`onUnmounted`。
- `defineEmits(['retitled'])`。
- State: `retitleModelId`（默认第一个模型 id 字符串）、`retitleRunning`、`retitleProgress`（文案）、`retitleCancelled`。
- `onUnmounted(() => { retitleCancelled.value = true })`。
- `onRebuildTitles`：
  1. 无模型则 return。
  2. `confirm('将用所选模型为所有未删除会话重新生成标题。已有标题（含手动修改）会被覆盖；没有消息的会话会跳过。')`，取消则 return。
  3. `retitleCancelled = false`，`retitleRunning = true`。
  4. `const sessions = await listSessions()`，`total = sessions.length`，计数 `ok/skipped/failed/done`。
  5. 循环：若 `retitleCancelled` 则 break；`retitleProgress = \`已完成 ${done}/${total}，失败 ${failed}\``；try `retitleSession`；`skipped: true` → skipped++；否则 ok++ 且 `emit('retitled')`；catch → failed++；`done = ok+skipped+failed`。
  6. 结束后若未被取消：`retitleProgress = \`完成：成功 ${ok}，跳过 ${skipped}（无消息），失败 ${failed}\``；`retitleRunning = false`。
- 模板：在「修改密码」section **之前**插入：

```html
    <section>
      <h2>重建会话标题</h2>
      <form class="password-form retitle-form" @submit.prevent="onRebuildTitles">
        <label>
          模型
          <select v-model="retitleModelId" :disabled="retitleRunning || !models.length">
            <option v-for="m in models" :key="m.id" :value="String(m.id)">{{ m.name }}</option>
          </select>
        </label>
        <button type="submit" :disabled="retitleRunning || !models.length">重建全部标题</button>
      </form>
      <p v-if="retitleProgress">{{ retitleProgress }}</p>
    </section>
```

- `loadModels` 之后：若 `models.length` 且当前 `retitleModelId` 空或不在列表中，设为 `String(models[0].id)`。

- [ ] **Step 3: AppShell 刷新列表**

`frontend/src/components/AppShell.vue` 的 `RouterView` 子组件增加 `@retitled="onSent"`（`onSent` 已是 `loadSessions`），或 `@retitled="loadSessions"`。

- [ ] **Step 4: CSS**

In `frontend/src/styles.css`，把 `.password-form` 的 input/select/focus/button 选择器并上 `.retitle-form`（与 `.password-form` 已共用的规则可只加 `select`）：

```css
.login input,
.model-select select,
.model-form input,
.password-form input,
.retitle-form select {
```

以及 focus 列表同样加上 `.retitle-form select:focus`。`.model-form, .password-form` 改为也包含 `.retitle-form`。label 规则同样。

- [ ] **Step 5: Run frontend tests**

Run: `cd frontend && npm test`

Expected: 现有测试 PASS。

- [ ] **Step 6: Commit**

Skip unless the user asked to commit.

---

## Self-Review

**Spec coverage:**

| Spec | Task |
|------|------|
| 设置页选模型 + 一按钮 + confirm | 5 |
| 全部 live session，无消息跳过 | 4, 5 |
| 失败继续并汇总 | 5 |
| POST retitle 400/404/skipped/200/502 | 4 |
| 不改 updated_at | 4 |
| system + 用户/助手转写，无 reasoning/图片，有文档文本 | 1, 4 |
| 非流式 chat_completion | 2 |
| 上下文超长 drop_oldest_turn | 3 |
| 清洗引号/换行/128 字；空标题失败 | 1, 3 |
| 离开设置停止后续请求 | 5 `onUnmounted` |
| 每成功一次刷新左栏 | 5 emit `retitled` |

**Placeholder scan:** 无 TBD / “implement later”。

**Type consistency:** `CompletionResult`、`generate_session_title(..., chat_fn=...)`、`RetitleIn.model_id: int`、前端 `retitleSession(id, modelId)` 前后任务一致。
