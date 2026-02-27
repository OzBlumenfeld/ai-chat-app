"""AES-ECB UUID masking for hiding UUIDv7 timestamps at the API boundary.

Internal DB UUIDs (UUIDv7) are encrypted before being sent to clients and
decrypted when received back, so the time-ordered bits are never exposed.
A single 16-byte AES block is used — ECB mode is safe here because there
is no repeating-block pattern to exploit on a single-block input.
"""

import uuid
from typing import Annotated, Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from pydantic import BeforeValidator, PlainSerializer


def _key() -> bytes:
    from app.config import settings

    return bytes.fromhex(settings.UUID_MASK_KEY)


def mask_uuid(u: uuid.UUID) -> uuid.UUID:
    """Encrypt a real internal UUID → opaque external UUID."""
    cipher = Cipher(algorithms.AES(_key()), modes.ECB())
    enc = cipher.encryptor()
    return uuid.UUID(bytes=enc.update(u.bytes) + enc.finalize())


def unmask_uuid(u: uuid.UUID) -> uuid.UUID:
    """Decrypt an opaque external UUID → real internal UUID."""
    cipher = Cipher(algorithms.AES(_key()), modes.ECB())
    dec = cipher.decryptor()
    return uuid.UUID(bytes=dec.update(u.bytes) + dec.finalize())


def _validate(v: Any) -> uuid.UUID:
    """Pydantic BeforeValidator: unmask string inputs (from clients), pass UUID objects through (from DB)."""
    if isinstance(v, uuid.UUID):
        return v
    if isinstance(v, str):
        return unmask_uuid(uuid.UUID(v))
    raise ValueError(f"Expected UUID or str, got {type(v)}")


def _serialize(v: uuid.UUID) -> str:
    """Pydantic PlainSerializer: mask the real UUID before serializing to JSON."""
    return str(mask_uuid(v))


MaskedUUID = Annotated[
    uuid.UUID,
    BeforeValidator(_validate),
    PlainSerializer(_serialize, return_type=str),
]
