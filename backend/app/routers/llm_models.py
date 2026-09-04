from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.tables import LlmModel, User

router = APIRouter(prefix="/api/models", tags=["models"])


class ModelIn(BaseModel):
    name: str
    base_url: str
    api_key: str | None = None
    model: str
    supports_vision: bool = False
    sort_order: int = 0


def _mask(key: str) -> str:
    if len(key) <= 4:
        return "****"
    return "****" + key[-4:]


def _out(row: LlmModel) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "base_url": row.base_url,
        "api_key_masked": _mask(row.api_key),
        "model": row.model,
        "supports_vision": row.supports_vision,
        "sort_order": row.sort_order,
    }


@router.get("")
def list_models(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(LlmModel).order_by(LlmModel.sort_order, LlmModel.id).all()
    return [_out(r) for r in rows]


@router.post("")
def create_model(
    body: ModelIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    if not body.api_key:
        raise HTTPException(status_code=400, detail="api_key 必填")
    row = LlmModel(
        name=body.name,
        base_url=body.base_url.rstrip("/"),
        api_key=body.api_key,
        model=body.model,
        supports_vision=body.supports_vision,
        sort_order=body.sort_order,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _out(row)


@router.patch("/{model_id}")
def update_model(
    model_id: int,
    body: ModelIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.get(LlmModel, model_id)
    if row is None:
        raise HTTPException(status_code=404, detail="模型不存在")
    row.name = body.name
    row.base_url = body.base_url.rstrip("/")
    row.model = body.model
    row.supports_vision = body.supports_vision
    row.sort_order = body.sort_order
    if body.api_key:
        row.api_key = body.api_key
    db.commit()
    db.refresh(row)
    return _out(row)


@router.delete("/{model_id}")
def delete_model(
    model_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    row = db.get(LlmModel, model_id)
    if row is None:
        raise HTTPException(status_code=404, detail="模型不存在")
    db.delete(row)
    db.commit()
    return {"ok": True}
