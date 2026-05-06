import base64
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plaintext password using Argon2."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against its hash."""
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: uuid.UUID) -> str:
    """Create a signed JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiry_minutes)
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.app_secret_key, algorithm="HS256")


def create_refresh_token(user_id: uuid.UUID) -> str:
    """Create a signed JWT refresh token with longer expiry."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expiry_days)
    payload = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.app_secret_key, algorithm="HS256")


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    return jwt.decode(token, settings.app_secret_key, algorithms=["HS256"])


def _get_aes_key() -> bytes:
    """Derive a 32-byte AES key from the hex ENCRYPTION_KEY env var."""
    key_hex = settings.encryption_key
    key_bytes = bytes.fromhex(key_hex)
    if len(key_bytes) != 32:
        raise ValueError("ENCRYPTION_KEY must be exactly 32 bytes (64 hex characters)")
    return key_bytes


def encrypt_token(plaintext: str) -> str:
    """
    Encrypt a string using AES-256-GCM.
    Returns a base64-encoded string of: IV (12 bytes) + ciphertext + tag.
    """
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    iv = os.urandom(12)
    ciphertext = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)
    return base64.b64encode(iv + ciphertext).decode("utf-8")


def decrypt_token(encrypted: str) -> str:
    """
    Decrypt an AES-256-GCM encrypted string.
    Expects a base64-encoded string of: IV (12 bytes) + ciphertext + tag.
    """
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    raw = base64.b64decode(encrypted.encode("utf-8"))
    iv = raw[:12]
    ciphertext = raw[12:]
    plaintext = aesgcm.decrypt(iv, ciphertext, None)
    return plaintext.decode("utf-8")