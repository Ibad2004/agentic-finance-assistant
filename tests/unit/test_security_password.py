from app.security.password import hash_password, verify_password


def test_password_hash_and_verify_success() -> None:
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)
    assert hashed.startswith("pbkdf2_sha256$600000$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_unique_salts_produce_different_hashes() -> None:
    password = "SamePasswordAcrossUsers"
    hash1 = hash_password(password)
    hash2 = hash_password(password)
    assert hash1 != hash2
    assert verify_password(password, hash1) is True
    assert verify_password(password, hash2) is True


def test_invalid_hash_format_returns_false() -> None:
    assert verify_password("password", "") is False
    assert verify_password("password", "invalid_format") is False
    assert verify_password("password", "pbkdf2_sha256$600000$corrupted") is False
    assert verify_password("", "pbkdf2_sha256$600000$1234$5678") is False
