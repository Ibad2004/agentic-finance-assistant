from datetime import timedelta
from uuid import uuid4

from app.security.jwt import create_access_token, decode_access_token


SECRET = "test_secret_key_12345678901234567890"


def test_jwt_create_and_decode_success() -> None:
    user_id = uuid4()
    token = create_access_token(user_id=user_id, secret_key=SECRET)
    decoded_user_id = decode_access_token(token=token, secret_key=SECRET)
    assert decoded_user_id == user_id


def test_jwt_with_wrong_secret_fails() -> None:
    user_id = uuid4()
    token = create_access_token(user_id=user_id, secret_key=SECRET)
    decoded = decode_access_token(token=token, secret_key="wrong_secret_key_1234567890")
    assert decoded is None


def test_expired_jwt_fails() -> None:
    user_id = uuid4()
    # Create expired token (-10 seconds)
    token = create_access_token(user_id=user_id, secret_key=SECRET, expires_delta=timedelta(seconds=-10))
    decoded = decode_access_token(token=token, secret_key=SECRET)
    assert decoded is None


def test_malformed_jwt_fails() -> None:
    assert decode_access_token("not.a.valid.jwt", secret_key=SECRET) is None
    assert decode_access_token("", secret_key=SECRET) is None
    assert decode_access_token("a.b", secret_key=SECRET) is None
