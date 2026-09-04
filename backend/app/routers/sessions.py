from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.tables import Attachment, ChatSession, Message, User

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _out(row: ChatSession) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def delete_session_files(db: Session, session_id: int) -> None:
    paths = (
        db.query(Attachment.storage_path)
        .join(Message, Attachment.message_id == Message.id)
        .filter(Message.session_id == session_id)
        .all()
    )
    for (p,) in paths:
        Path(p).unlink(missing_ok=True)


@router.get("")
def list_sessions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(ChatSession).order_by(ChatSession.updated_at.desc()).all()
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
    row = db.get(ChatSession, session_id)
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
    row = db.get(ChatSession, session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    delete_session_files(db, session_id)
    db.delete(row)
    db.commit()
    return {"ok": True}
