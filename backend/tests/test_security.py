from app.security import hash_password, read_session, sign_session, verify_password


def test_password_roundtrip():
    hashed = hash_password("passpass")
    assert verify_password("passpass", hashed)
    assert not verify_password("wrong", hashed)


def test_session_cookie_roundtrip():
    secret = "secret-secret-secret-secret"
    token = sign_session(1, 3, secret)
    assert read_session(token, secret) == (1, 3)
    assert read_session(token, "other-secret-other-secret") is None
    assert read_session("not-a-token", secret) is None
