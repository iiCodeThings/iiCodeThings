from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import get_current_user
from app.routers.sessions import get_live_session
from app.services.turns import public_message
from app.tables import Message, Share, User

router = APIRouter(tags=["shares"])


class TurnShareIn(BaseModel):
    user_message_id: int


def _share_out(row: Share) -> dict:
    return {"token": row.token, "path": f"/s/{row.token}"}


def _get_or_create_share(
    db: Session, *, session_id: int, kind: str, user_message_id: int | None
) -> Share:
    q = db.query(Share).filter(Share.session_id == session_id, Share.kind == kind)
    if user_message_id is None:
        q = q.filter(Share.user_message_id.is_(None))
    else:
        q = q.filter(Share.user_message_id == user_message_id)
    row = q.first()
    if row is not None:
        return row
    row = Share(
        token=secrets.token_urlsafe(16),
        kind=kind,
        session_id=session_id,
        user_message_id=user_message_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _resolve_share(db: Session, token: str) -> tuple:
    row = db.query(Share).filter(Share.token == token).first()
    if row is None:
        raise HTTPException(status_code=404, detail="分享不存在")
    session = get_live_session(db, row.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="分享不存在")
    q = (
        db.query(Message)
        .options(selectinload(Message.attachments))
        .filter(Message.session_id == session.id)
        .order_by(Message.id.asc())
    )
    if row.kind == "session":
        messages = q.all()
    else:
        user = (
            db.query(Message)
            .options(selectinload(Message.attachments))
            .filter(Message.id == row.user_message_id)
            .first()
        )
        if user is None or user.session_id != session.id or user.role != "user":
            raise HTTPException(status_code=404, detail="分享不存在")
        asst = (
            db.query(Message)
            .options(selectinload(Message.attachments))
            .filter(
                Message.session_id == session.id,
                Message.id > user.id,
                Message.role == "assistant",
            )
            .order_by(Message.id.asc())
            .first()
        )
        messages = [user] + ([asst] if asst else [])
    return session, row, messages


@router.post("/api/sessions/{session_id}/share")
def create_session_share(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = get_live_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return _share_out(_get_or_create_share(db, session_id=session.id, kind="session", user_message_id=None))


@router.post("/api/sessions/{session_id}/share/turn")
def create_turn_share(
    session_id: int,
    body: TurnShareIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = get_live_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    msg = db.get(Message, body.user_message_id)
    if msg is None or msg.session_id != session.id or msg.role != "user":
        raise HTTPException(status_code=400, detail="无法分享这一轮")
    return _share_out(
        _get_or_create_share(
            db, session_id=session.id, kind="turn", user_message_id=msg.id
        )
    )


@router.get("/api/shares/{token}")
def get_share(token: str, db: Session = Depends(get_db)):
    session, row, messages = _resolve_share(db, token)
    return {
        "kind": row.kind,
        "title": session.title,
        "messages": [public_message(m) for m in messages],
    }
