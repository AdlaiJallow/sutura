"""Opaque token generation/hashing for refresh, email-verification, and password-reset tokens.
Only the hash is ever persisted; the raw token is shown to the user exactly once.
"""
import hashlib
import secrets


def generate_raw_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
