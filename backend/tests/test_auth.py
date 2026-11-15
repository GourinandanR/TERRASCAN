import pytest
from app.auth import hash_password, verify_password, issue_token, token_digest, token_is_expired

def test_password_hashing_round_trip():
    salt, digest = hash_password("Correct-Horse-Battery-7")
    assert verify_password("Correct-Horse-Battery-7", salt, digest)
    assert not verify_password("incorrect-password", salt, digest)

def test_password_minimum_length():
    with pytest.raises(ValueError):
        hash_password("short")

def test_session_tokens_are_hashed():
    raw, digest = issue_token()
    assert raw != digest
    assert token_digest(raw) == digest

def test_invalid_expiry_fails_closed():
    assert token_is_expired("not-a-date")
