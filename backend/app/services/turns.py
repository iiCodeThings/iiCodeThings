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
