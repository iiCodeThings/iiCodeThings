from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.services.search import search_messages, search_sessions
from app.tables import User

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/messages")
def search_message_hits(
    q: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return {"messages": search_messages(db, q)}


@router.get("")
def search(q: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"sessions": search_sessions(db, q)}
