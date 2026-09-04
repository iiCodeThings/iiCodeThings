from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.security import hash_password, sign_session, verify_password
from app.tables import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    username: str
    password: str


class PasswordBody(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6)


def _set_cookie(response: Response, request: Request, user: User) -> None:
    settings = request.app.state.settings
    token = sign_session(user.id, user.token_version, settings.session_secret)
    response.set_cookie(
        settings.cookie_name,
        token,
        max_age=settings.cookie_max_age,
        httponly=True,
        samesite="lax",
        path="/",
    )


@router.post("/login")
def login(body: LoginBody, request: Request, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    _set_cookie(response, request, user)
    return {"ok": True}


@router.post("/logout")
def logout(request: Request, response: Response):
    response.delete_cookie(request.app.state.settings.cookie_name, path="/")
    return {"ok": True}


@router.post("/password")
def change_password(
    body: PasswordBody,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    user.password_hash = hash_password(body.new_password)
    user.token_version += 1
    db.commit()
    response.delete_cookie(request.app.state.settings.cookie_name, path="/")
    return {"ok": True}
