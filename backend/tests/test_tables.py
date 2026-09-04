from app.security import hash_password
from app.tables import User


def test_seed_creates_single_user(db, settings):
    from app.db import seed_default_user

    seed_default_user(db, settings.app_username, hash_password(settings.app_password))
    seed_default_user(db, settings.app_username, hash_password("other"))
    users = db.query(User).all()
    assert len(users) == 1
    assert users[0].username == "admin"
    assert users[0].token_version == 0
