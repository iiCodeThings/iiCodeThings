from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.tables import ChatSession, Message


def tokenize_query(q: str) -> list[str]:
    return [t for t in (q or "").split() if t]


def like_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _title_has_all(title: str, tokens: list[str]) -> bool:
    return all(tok in title for tok in tokens)


def search_sessions(db: Session, q: str) -> list[dict]:
    tokens = tokenize_query(q)
    query = (
        db.query(ChatSession)
        .options(selectinload(ChatSession.messages))
        .filter(ChatSession.deleted_at.is_(None))
        .order_by(ChatSession.updated_at.desc())
    )
    if tokens:
        for tok in tokens:
            pattern = f"%{like_escape(tok)}%"
            query = query.filter(
                or_(
                    ChatSession.title.like(pattern, escape="\\"),
                    ChatSession.messages.any(Message.content.like(pattern, escape="\\")),
                )
            )
    rows = query.all()
    out: list[dict] = []
    for row in rows:
        if not tokens:
            out.append(
                {
                    "id": row.id,
                    "title": row.title,
                    "updated_at": row.updated_at,
                    "snippet": "",
                    "hit_message_id": None,
                }
            )
            continue
        if _title_has_all(row.title, tokens):
            out.append(
                {
                    "id": row.id,
                    "title": row.title,
                    "updated_at": row.updated_at,
                    "snippet": row.title[:80],
                    "hit_message_id": None,
                }
            )
            continue
        hit = None
        for msg in sorted(row.messages, key=lambda m: m.id):
            if any(tok in (msg.content or "") for tok in tokens):
                hit = msg
                break
        out.append(
            {
                "id": row.id,
                "title": row.title,
                "updated_at": row.updated_at,
                "snippet": (hit.content[:80] if hit else row.title[:80]),
                "hit_message_id": hit.id if hit else None,
            }
        )
    return out
