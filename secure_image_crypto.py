"""Authenticated, password-based image encryption for Cipher Arcade.

Container format v1 stores only image dimensions, a random salt, a random
AES-GCM nonce, and authenticated ciphertext. Image samples are normalized to
RGB and encrypted as raw bytes so pixel statistics compare like-for-like.
"""

from __future__ import annotations

import io
import secrets
import struct
import warnings
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from PIL import Image, ImageOps


MAGIC = b"VCLAB\x01"
HEADER = struct.Struct(">6sII16s12s")
HEADER_SIZE = HEADER.size
TAG_SIZE = 16
SALT_SIZE = 16
NONCE_SIZE = 12
MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 256
MAX_IMAGE_PIXELS = 8_000_000
MAX_SOURCE_BYTES = 10 * 1024 * 1024
MAX_CONTAINER_BYTES = 32 * 1024 * 1024


class InvalidContainerError(ValueError):
    """The input is not a supported or well-formed Cipher Arcade container."""


class PasswordPolicyError(ValueError):
    """The chosen encryption passphrase is too short."""


@dataclass(frozen=True)
class NormalizedImage:
    width: int
    height: int
    pixels: bytes


@dataclass(frozen=True)
class DecryptedImage:
    image: Image.Image
    pixels: bytes
    encrypted_pixels: bytes


def normalize_image(image_bytes: bytes) -> NormalizedImage:
    """Decode an image, honor its orientation, composite transparency on white."""
    if len(image_bytes) > MAX_SOURCE_BYTES:
        raise ValueError("图片文件不能超过 10 MiB。")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(image_bytes)) as source:
                width, height = source.size
                if width < 1 or height < 1 or width * height > MAX_IMAGE_PIXELS:
                    raise ValueError("图片最多支持 800 万像素。")
                source.load()
                oriented = ImageOps.exif_transpose(source)
                rgba = oriented.convert("RGBA")
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError("图片尺寸过大，已停止解码。") from exc
    except (OSError, Image.UnidentifiedImageError) as exc:
        raise ValueError("无法解码图片，请选择有效的 PNG 或 JPEG。") from exc

    canvas = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    rgb = Image.alpha_composite(canvas, rgba).convert("RGB")
    return NormalizedImage(rgb.width, rgb.height, rgb.tobytes())


def _derive_key(password: str, salt: bytes) -> bytes:
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"口令不能超过 {MAX_PASSWORD_LENGTH} 个字符。")
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    return kdf.derive(password.encode("utf-8"))


def encrypt_pixels(pixels: bytes, width: int, height: int, password: str) -> bytes:
    """Encrypt RGB samples into a versioned AES-256-GCM container."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordPolicyError(f"口令至少需要 {MIN_PASSWORD_LENGTH} 个字符。")
    if width < 1 or height < 1 or width * height > MAX_IMAGE_PIXELS:
        raise ValueError("图像宽高无效或超过 800 万像素上限。")
    if len(pixels) != width * height * 3:
        raise ValueError("RGB 像素数据长度与图像尺寸不匹配。")

    salt = secrets.token_bytes(SALT_SIZE)
    nonce = secrets.token_bytes(NONCE_SIZE)
    header = HEADER.pack(MAGIC, width, height, salt, nonce)
    key = _derive_key(password, salt)
    ciphertext = AESGCM(key).encrypt(nonce, pixels, header)
    return header + ciphertext


def decrypt_container(container: bytes, password: str) -> DecryptedImage:
    """Authenticate and decrypt a v1 container; invalid tags are never ignored."""
    if len(container) > MAX_CONTAINER_BYTES:
        raise InvalidContainerError("加密包超过 32 MiB 上限。")
    if len(container) < HEADER_SIZE + TAG_SIZE:
        raise InvalidContainerError("文件太短，不是完整的加密包。")

    header = container[:HEADER_SIZE]
    try:
        magic, width, height, salt, nonce = HEADER.unpack(header)
    except struct.error as exc:
        raise InvalidContainerError("加密包头格式错误。") from exc

    if magic != MAGIC:
        raise InvalidContainerError("文件格式不受支持，或版本号不正确。")
    if width < 1 or height < 1 or width * height > MAX_IMAGE_PIXELS:
        raise InvalidContainerError("加密包中的图像尺寸无效。")

    encrypted = container[HEADER_SIZE:]
    expected_length = width * height * 3 + TAG_SIZE
    if len(encrypted) != expected_length:
        raise InvalidContainerError("加密包长度与声明的图像尺寸不匹配。")

    key = _derive_key(password, salt)
    pixels = AESGCM(key).decrypt(nonce, encrypted, header)
    image = Image.frombytes("RGB", (width, height), pixels)
    return DecryptedImage(
        image=image,
        pixels=pixels,
        encrypted_pixels=encrypted[:-TAG_SIZE],
    )
