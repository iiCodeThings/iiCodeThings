from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.security import read_session
from app.tables import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    settings = request.app.state.settings
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    parsed = read_session(token, settings.session_secret)
    if parsed is None:
        raise HTTPException(status_code=401, detail="未登录")
    user_id, token_version = parsed
    user = db.get(User, user_id)
    if user is None or user.token_version != token_version:
        raise HTTPException(status_code=401, detail="未登录")
    return user
