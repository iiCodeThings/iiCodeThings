from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.db import get_db
from app.deps import get_current_user
from app.services.attachments import UploadRejected, classify, extract_text, save_bytes
from app.services.context import build_openai_messages, drop_oldest_turn, is_context_length_error
from app.services.llm import stream_chat_completion
from app.tables import Attachment, ChatSession, LlmModel, Message, User
from app.title import auto_title

router = APIRouter(prefix="/api/sessions", tags=["messages"])


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _to_item(msg: Message) -> dict:
    return {
        "role": msg.role,
        "content": msg.content or "",
        "attachments": [
            {
                "kind": a.kind,
                "storage_path": a.storage_path,
                "extracted_text": a.extracted_text,
            }
            for a in msg.attachments
        ],
    }


async def _generate(
    bind: Engine, session_id: int, model_id: int, user_msg_id: int
) -> AsyncIterator[str]:
    StreamSession = sessionmaker(bind=bind, autoflush=False, autocommit=False)
    db = StreamSession()
    try:
        session = db.get(ChatSession, session_id)
        model_row = db.get(LlmModel, model_id)
        user_msg = (
            db.query(Message)
            .options(selectinload(Message.attachments))
            .filter(Message.id == user_msg_id)
            .one()
        )
        rows = (
            db.query(Message)
            .options(selectinload(Message.attachments))
            .filter(Message.session_id == session.id)
            .order_by(Message.id.asc())
            .all()
        )
        items = [_to_item(m) for m in rows]
        while True:
            openai_msgs = build_openai_messages(items)
            failed, failed_status = None, 0
            content_acc, reasoning_acc = "", ""
            async for ev in stream_chat_completion(
                base_url=model_row.base_url,
                api_key=model_row.api_key,
                model=model_row.model,
                messages=openai_msgs,
            ):
                if ev.kind == "error":
                    failed, failed_status = ev.text, ev.status_code or 500
                    break
                if ev.kind == "delta":
                    content_acc += ev.text
                    yield _sse("delta", {"text": ev.text})
                elif ev.kind == "reasoning":
                    reasoning_acc += ev.text
                    yield _sse("reasoning", {"text": ev.text})
                elif ev.kind == "done":
                    break
            if failed is not None:
                if is_context_length_error(failed_status, failed) and len(items) > 1:
                    items = drop_oldest_turn(items)
                    yield _sse("truncated", {"text": "上下文过长，已截断较早消息"})
                    continue
                yield _sse("error", {"text": failed})
                return
            assistant = Message(
                session_id=session.id,
                role="assistant",
                content=content_acc,
                reasoning=reasoning_acc or None,
                model_name=model_row.name,
                model=model_row.model,
            )
            db.add(assistant)
            session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            if session.title == "新对话":
                first_name = (
                    user_msg.attachments[0].original_filename if user_msg.attachments else None
                )
                session.title = auto_title(user_msg.content, first_name)
            db.commit()
            db.refresh(assistant)
            yield _sse("done", {"message_id": assistant.id})
            return
    finally:
        db.close()


@router.post("/{session_id}/messages")
async def send_message(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    form = await request.form()
    content = str(form.get("content") or "")
    model_id_raw = form.get("model_id")
    uploads = [v for k, v in form.multi_items() if k == "files" and hasattr(v, "filename")]
    settings = request.app.state.settings
    session = db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    if not model_id_raw:
        raise HTTPException(status_code=400, detail="请先在设置中添加模型")
    try:
        model_id = int(model_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="请先在设置中添加模型")
    model_row = db.get(LlmModel, model_id)
    if model_row is None:
        raise HTTPException(status_code=400, detail="请先在设置中添加模型")
    if not content.strip() and not uploads:
        raise HTTPException(status_code=400, detail="请输入内容或上传文件")
    buffers: list[tuple[str, bytes, str]] = []
    try:
        for f in uploads:
            raw = await f.read()
            classify(f.filename or "")
            buffers.append((f.filename or "file", raw, f.content_type or "application/octet-stream"))
    except UploadRejected as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    if any(classify(name) == "image" for name, _, _ in buffers) and not model_row.supports_vision:
        raise HTTPException(status_code=400, detail="请更换支持视觉的模型")
    user_msg = Message(
        session_id=session.id,
        role="user",
        content=content,
        reasoning=None,
        model_name=model_row.name,
        model=model_row.model,
    )
    db.add(user_msg)
    db.flush()
    for filename, raw, mime in buffers:
        try:
            path = save_bytes(
                settings.upload_dir, user_msg.id, filename, raw, settings.max_upload_bytes
            )
        except UploadRejected as exc:
            db.rollback()
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        kind = classify(filename)
        extracted = extract_text(path, Path(filename).suffix) if kind == "document" else None
        db.add(
            Attachment(
                message_id=user_msg.id,
                kind=kind,
                original_filename=filename,
                mime_type=mime,
                storage_path=path,
                extracted_text=extracted,
            )
        )
    db.commit()
    user_msg = (
        db.query(Message)
        .options(selectinload(Message.attachments))
        .filter(Message.id == user_msg.id)
        .one()
    )
    return StreamingResponse(
        _generate(db.get_bind(), session.id, model_row.id, user_msg.id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
