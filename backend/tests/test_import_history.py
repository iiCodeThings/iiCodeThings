from pathlib import Path

from app.db import get_engine, init_db
from app.import_history import import_history
from app.tables import ChatSession, Message


def _make_history(path: Path) -> None:
    import sqlite3

    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id STRING(64) NOT NULL,
            question TEXT NOT NULL,
            reason TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_time DATETIME,
            source varchar(32)
        )
        """
    )
    conn.executemany(
        "INSERT INTO history (session_id, question, reason, answer, created_time, source) "
        "VALUES (?,?,?,?,?,?)",
        [
            (
                "sid-a",
                "社会学的想象力具体指什么？",
                "先想定义",
                "指把个人困扰放到社会结构中理解。",
                "2025-03-21 03:00:31",
                "socrates",
            ),
            (
                "sid-a",
                "再举个例子",
                "",
                "失业既是个人经历，也是经济结构问题。",
                "2025-03-21 03:05:00",
                "socrates",
            ),
            (
                "sid-b",
                "什么是文化资本",
                "分析布迪厄",
                "家庭传承的品味、学历与惯习。",
                "2025-03-22 10:00:00",
                "DeepSeek推理",
            ),
        ],
    )
    conn.commit()
    conn.close()


def test_import_history_maps_turns_and_is_idempotent(tmp_path, settings):
    src = tmp_path / "history.db"
    _make_history(src)
    engine = get_engine(settings)
    init_db(engine)

    stats = import_history(src, engine)
    assert stats == {"sessions_created": 2, "sessions_skipped": 0, "messages_created": 6}

    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        sessions = db.query(ChatSession).order_by(ChatSession.id.asc()).all()
        assert len(sessions) == 2
        assert sessions[0].title == "社会学的想象力具体指什么？"
        msgs = (
            db.query(Message)
            .filter(Message.session_id == sessions[0].id)
            .order_by(Message.id.asc())
            .all()
        )
        assert [m.role for m in msgs] == ["user", "assistant", "user", "assistant"]
        assert msgs[1].reasoning == "先想定义"
        assert msgs[3].reasoning is None
        assert msgs[0].model_name == "socrates"
        assert sessions[1].title == "什么是文化资本"
        b_msgs = db.query(Message).filter(Message.session_id == sessions[1].id).all()
        assert b_msgs[0].model_name == "DeepSeek推理"
    finally:
        db.close()

    again = import_history(src, engine)
    assert again == {"sessions_created": 0, "sessions_skipped": 2, "messages_created": 0}
    db = SessionLocal()
    try:
        assert db.query(ChatSession).count() == 2
        assert db.query(Message).count() == 6
    finally:
        db.close()
