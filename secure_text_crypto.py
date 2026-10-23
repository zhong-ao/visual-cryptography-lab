"""Password-based authenticated encryption for short text notes."""

from __future__ import annotations

import base64
import binascii
import secrets
import struct

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


MAGIC = b"CLTXT\x01"
HEADER = struct.Struct(">6s16s12s")
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 256
MAX_PLAINTEXT_BYTES = 20_000
TAG_SIZE = 16
TOKEN_PREFIX = "CLTEXT1:"


class InvalidTextPackageError(ValueError):
    """The pasted token is malformed or uses an unsupported format."""


class PasswordPolicyError(ValueError):
    """The selected passphrase does not meet the local length policy."""


def _derive_key(password: str, salt: bytes) -> bytes:
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"口令不能超过 {MAX_PASSWORD_LENGTH} 个字符。")
    return Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(
        password.encode("utf-8")
    )


def encrypt_text(plaintext: str, password: str) -> str:
    """Return a printable, versioned AES-GCM token for a short UTF-8 note."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordPolicyError(f"口令至少需要 {MIN_PASSWORD_LENGTH} 个字符。")
    raw = plaintext.encode("utf-8")
    if len(raw) > MAX_PLAINTEXT_BYTES:
        raise ValueError("便笺最多支持 20 KB 文本。")

    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    header = HEADER.pack(MAGIC, salt, nonce)
    ciphertext = AESGCM(_derive_key(password, salt)).encrypt(nonce, raw, header)
    token = base64.urlsafe_b64encode(header + ciphertext).decode("ascii")
    return TOKEN_PREFIX + token


def decrypt_text(token: str, password: str) -> str:
    """Authenticate and decrypt a text token; InvalidTag is intentionally raised."""
    compact = "".join(token.split())
    if not compact.startswith(TOKEN_PREFIX):
        raise InvalidTextPackageError("没有识别到 CLTEXT1 便笺头。")

    encoded = compact[len(TOKEN_PREFIX):]
    if not encoded or len(encoded) > 40_000:
        raise InvalidTextPackageError("便笺包为空或超过允许长度。")
    padded = encoded + "=" * ((-len(encoded)) % 4)
    try:
        package = base64.b64decode(padded, altchars=b"-_", validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InvalidTextPackageError("便笺包不是有效的 Base64 文本。") from exc

    if len(package) < HEADER.size + TAG_SIZE:
        raise InvalidTextPackageError("便笺包不完整。")
    header = package[: HEADER.size]
    magic, salt, nonce = HEADER.unpack(header)
    if magic != MAGIC:
        raise InvalidTextPackageError("便笺格式版本不受支持。")

    ciphertext = package[HEADER.size:]
    if len(ciphertext) > MAX_PLAINTEXT_BYTES + TAG_SIZE:
        raise InvalidTextPackageError("便笺文本超过允许长度。")
    plaintext = AESGCM(_derive_key(password, salt)).decrypt(nonce, ciphertext, header)
    try:
        return plaintext.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidTextPackageError("认证通过，但内容不是有效 UTF-8 文本。") from exc
