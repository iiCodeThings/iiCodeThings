from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.tables import ChatSession, Message
from app.title import auto_title

MAP_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS history_import_map (
    old_session_id VARCHAR(64) NOT NULL PRIMARY KEY,
    new_session_id INTEGER NOT NULL
)
"""


def parse_dt(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    raw = str(value or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return datetime.fromisoformat(raw)


def _ensure_map_table(db: Session) -> None:
    db.execute(text(MAP_TABLE_SQL))
    db.commit()


def _mapped_id(db: Session, old_session_id: str) -> int | None:
    row = db.execute(
        text("SELECT new_session_id FROM history_import_map WHERE old_session_id = :old"),
        {"old": old_session_id},
    ).first()
    return int(row[0]) if row else None


def import_history(history_path: Path, engine: Engine) -> dict[str, int]:
    src = sqlite3.connect(str(history_path))
    src.row_factory = sqlite3.Row
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = SessionLocal()
    stats = {"sessions_created": 0, "sessions_skipped": 0, "messages_created": 0}
    try:
        _ensure_map_table(db)
        old_ids = [
            r[0]
            for r in src.execute(
                "SELECT session_id FROM history GROUP BY session_id ORDER BY MIN(id)"
            )
        ]
        for old_id in old_ids:
            if _mapped_id(db, old_id) is not None:
                stats["sessions_skipped"] += 1
                continue
            turns = src.execute(
                """
                SELECT question, reason, answer, created_time, source
                FROM history
                WHERE session_id = ?
                ORDER BY created_time, id
                """,
                (old_id,),
            ).fetchall()
            if not turns:
                continue
            times = [parse_dt(t["created_time"]) for t in turns]
            first = turns[0]
            source = (first["source"] or "").strip() or "imported"
            session = ChatSession(
                title=auto_title(first["question"], None),
                created_at=min(times),
                updated_at=max(times),
            )
            db.add(session)
            db.flush()
            for turn, created in zip(turns, times):
                db.add(
                    Message(
                        session_id=session.id,
                        role="user",
                        content=turn["question"] or "",
                        reasoning=None,
                        model_name=source,
                        model=source,
                        created_at=created,
                    )
                )
                reason = (turn["reason"] or "").strip() or None
                db.add(
                    Message(
                        session_id=session.id,
                        role="assistant",
                        content=turn["answer"] or "",
                        reasoning=reason,
                        model_name=source,
                        model=source,
                        created_at=created,
                    )
                )
                stats["messages_created"] += 2
            db.execute(
                text(
                    "INSERT INTO history_import_map (old_session_id, new_session_id) "
                    "VALUES (:old, :new)"
                ),
                {"old": old_id, "new": session.id},
            )
            stats["sessions_created"] += 1
        db.commit()
        return stats
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        src.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import history.db into the chat database")
    parser.add_argument(
        "history_db",
        nargs="?",
        default=str(Path(__file__).resolve().parents[2] / "history.db"),
        help="Path to the old SQLite history.db",
    )
    args = parser.parse_args()
    from app.config import load_settings
    from app.db import get_engine, init_db

    settings = load_settings()
    engine = get_engine(settings)
    init_db(engine)
    stats = import_history(Path(args.history_db), engine)
    print(
        f"imported sessions={stats['sessions_created']} "
        f"skipped={stats['sessions_skipped']} "
        f"messages={stats['messages_created']}"
    )


if __name__ == "__main__":
    main()
