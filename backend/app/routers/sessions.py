from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import get_current_user
from app.services.retitle import TitleGenerationError, generate_session_title
from app.tables import ChatSession, LlmModel, Message, User
from app.title import turns_from_messages

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _out(row: ChatSession) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "pinned": row.pinned_at is not None,
    }


def get_live_session(db: Session, session_id: int) -> ChatSession | None:
    row = db.get(ChatSession, session_id)
    if row is None or row.deleted_at is not None:
        return None
    return row


def _write_pin(db: Session, row: ChatSession, pinned_at: datetime | None) -> ChatSession:
    # Keep updated_at unchanged: override Column.onupdate without rebinding a
    # datetime (SQLite TEXT would gain ".000000" and break sort ties).
    db.query(ChatSession).filter(ChatSession.id == row.id).update(
        {"pinned_at": pinned_at, "updated_at": ChatSession.updated_at},
        synchronize_session="fetch",
    )
    db.commit()
    db.refresh(row)
    return row


@router.get("")
def list_sessions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(ChatSession)
        .filter(ChatSession.deleted_at.is_(None))
        .order_by(
            ChatSession.pinned_at.is_(None),
            ChatSession.pinned_at.desc(),
            ChatSession.updated_at.desc(),
            ChatSession.id.desc(),
        )
        .all()
    )
    return [_out(r) for r in rows]


@router.post("")
def create_session(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = ChatSession(title="新对话")
    db.add(row)
    db.commit()
    db.refresh(row)
    return _out(row)


class TitleIn(BaseModel):
    title: str


@router.patch("/{session_id}")
def patch_session(
    session_id: int,
    body: TitleIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = get_live_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    row.title = body.title[:128]
    db.commit()
    db.refresh(row)
    return _out(row)


@router.delete("/{session_id}")
def delete_session(
    session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    row = get_live_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    row.deleted_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


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
