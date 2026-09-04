import hashlib
import hmac
import os

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

MAX_AGE = 60 * 60 * 24 * 30


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}${dk.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt_hex, dk_hex = password_hash.split("$", 1)
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(dk_hex)
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return hmac.compare_digest(actual, expected)


def _serializer(secret: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret, salt="chat-session")


def sign_session(user_id: int, token_version: int, secret: str) -> str:
    return _serializer(secret).dumps({"user_id": user_id, "token_version": token_version})


def read_session(token: str, secret: str) -> tuple[int, int] | None:
    try:
        data = _serializer(secret).loads(token, max_age=MAX_AGE)
        return int(data["user_id"]), int(data["token_version"])
    except (BadSignature, SignatureExpired, KeyError, TypeError, ValueError):
        return None
