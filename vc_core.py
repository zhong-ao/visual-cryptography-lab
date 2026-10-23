"""Core routines for a small (2, 2) visual cryptography laboratory."""

from __future__ import annotations

import secrets

import numpy as np
from PIL import Image, ImageOps


def preprocess_image(
    image: Image.Image, threshold: int = 128, max_side: int = 320
) -> np.ndarray:
    """Return a small binary image (0 = black, 1 = white).

    EXIF orientation is respected, transparency is composited over white, and
    large uploads are resized before the shares expand each source pixel 2x2.
    """
    if not 0 <= threshold <= 255:
        raise ValueError("threshold must be between 0 and 255")
    if max_side < 1:
        raise ValueError("max_side must be positive")

    oriented = ImageOps.exif_transpose(image)
    rgba = oriented.convert("RGBA")
    background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    gray = Image.alpha_composite(background, rgba).convert("L")

    width, height = gray.size
    scale = min(1.0, max_side / max(width, height))
    if scale < 1.0:
        new_size = (max(1, round(width * scale)), max(1, round(height * scale)))
        gray = gray.resize(new_size, Image.Resampling.LANCZOS)

    return (np.asarray(gray) > threshold).astype(np.uint8)


def encrypt_visual_share(binary_img: np.ndarray) -> tuple[Image.Image, Image.Image]:
    """Create two random 2x2-expanded shares for a (2, 2) VCS.

    Each block in Share 1 contains two white and two black subpixels. For a
    white source pixel, Share 2 uses the same block; for a black source pixel,
    it uses the complementary block. The low two bits of OS-generated random
    bytes select among four balanced patterns, so every pattern is equiprobable.
    """
    binary = np.asarray(binary_img)
    if binary.ndim != 2 or binary.size == 0:
        raise ValueError("binary_img must be a non-empty 2D array")
    binary = (binary > 0).astype(np.uint8)
    height, width = binary.shape

    patterns = np.array(
        [
            [[255, 0], [0, 255]],
            [[0, 255], [255, 0]],
            [[255, 255], [0, 0]],
            [[0, 0], [255, 255]],
        ],
        dtype=np.uint8,
    )

    pattern_ids = np.frombuffer(
        secrets.token_bytes(height * width), dtype=np.uint8
    ).reshape(height, width) & 0b11
    blocks = patterns[pattern_ids]
    complementary_blocks = 255 - blocks
    share2_blocks = np.where(binary[:, :, None, None] == 1, blocks, complementary_blocks)

    share1 = blocks.transpose(0, 2, 1, 3).reshape(height * 2, width * 2)
    share2 = share2_blocks.transpose(0, 2, 1, 3).reshape(height * 2, width * 2)
    return Image.fromarray(share1), Image.fromarray(share2)


def overlay_shares(share1_img: Image.Image, share2_img: Image.Image) -> Image.Image:
    """Simulate physical stacking by keeping only subpixels white in both shares."""
    share1 = np.asarray(share1_img.convert("L"))
    share2 = np.asarray(share2_img.convert("L"))
    if share1.shape != share2.shape:
        raise ValueError("the two shares must have the same dimensions")
    return Image.fromarray(np.minimum(share1, share2))


def calculate_shannon_entropy(img_array: np.ndarray) -> float:
    """Calculate the Shannon entropy of a binary or grayscale image in bits."""
    array = np.asarray(img_array)
    if array.size == 0:
        return 0.0
    if float(np.max(array)) <= 1.0:
        bits = (array > 0).astype(np.uint8)
    else:
        bits = (array > 128).astype(np.uint8)
    counts = np.bincount(bits.ravel(), minlength=2)
    probabilities = counts[counts > 0] / bits.size
    return float(-np.sum(probabilities * np.log2(probabilities)))


def calculate_adjacent_correlation(
    img_array: np.ndarray,
    num_samples: int = 2000,
    direction: str = "horizontal",
    seed: int = 0,
) -> tuple[float, np.ndarray, np.ndarray]:
    """Estimate adjacent-pixel Pearson correlation and return jittered plot points.

    Sampling and display jitter use a fixed diagnostic seed to keep reports
    reproducible. This RNG is only for analysis; share generation uses OS entropy.
    """
    array = np.asarray(img_array, dtype=float)
    if array.ndim != 2 or array.size == 0:
        raise ValueError("img_array must be a non-empty 2D array")
    if num_samples < 1:
        raise ValueError("num_samples must be positive")
    if direction not in {"horizontal", "vertical"}:
        raise ValueError("direction must be 'horizontal' or 'vertical'")

    height, width = array.shape
    pair_count = (
        height * max(width - 1, 0)
        if direction == "horizontal"
        else max(height - 1, 0) * width
    )
    rng = np.random.default_rng(seed)
    if pair_count == 0:
        empty = np.array([], dtype=float)
        return 0.0, empty, empty

    positions = rng.choice(pair_count, size=min(num_samples, pair_count), replace=False)
    if direction == "horizontal":
        rows, columns = np.divmod(positions, width - 1)
        x, y = array[rows, columns], array[rows, columns + 1]
    else:
        rows, columns = np.divmod(positions, width)
        x, y = array[rows, columns], array[rows + 1, columns]

    centered_x = x - np.mean(x)
    centered_y = y - np.mean(y)
    denominator = np.sqrt(np.sum(centered_x**2) * np.sum(centered_y**2))
    correlation = (
        0.0
        if denominator == 0
        else float(np.sum(centered_x * centered_y) / denominator)
    )

    x_scatter = x + rng.normal(0, 3, size=x.size)
    y_scatter = y + rng.normal(0, 3, size=y.size)
    return correlation, x_scatter, y_scatter


def calculate_share_balance(binary_img: np.ndarray, share_img: Image.Image) -> dict[str, float]:
    """Compare a share's white-pixel rate over white and black source blocks.

    A zero difference is an empirical check that this share's pixel balance does
    not reveal which source-pixel class it came from.
    """
    binary = np.asarray(binary_img)
    if binary.ndim != 2 or binary.size == 0:
        raise ValueError("binary_img must be a non-empty 2D array")
    share = np.asarray(share_img.convert("L"))
    expected_shape = (binary.shape[0] * 2, binary.shape[1] * 2)
    if share.shape != expected_shape:
        raise ValueError("share dimensions must be exactly twice the source dimensions")

    source_white = np.repeat(np.repeat(binary > 0, 2, axis=0), 2, axis=1)
    share_white = share > 128
    rates: dict[str, float] = {}
    for label, mask in (("white_source_rate", source_white), ("black_source_rate", ~source_white)):
        rates[label] = float(np.mean(share_white[mask])) if np.any(mask) else float("nan")

    white_rate = rates["white_source_rate"]
    black_rate = rates["black_source_rate"]
    rates["balance_gap"] = (
        abs(white_rate - black_rate)
        if np.isfinite(white_rate) and np.isfinite(black_rate)
        else float("nan")
    )
    return rates


def calculate_theoretical_contrast(binary_orig: np.ndarray, recovered_img: Image.Image) -> dict[str, float]:
    """Measure recovered white transmission and contrast alpha.

    For the 2x2 basis used here, an original white pixel retains two white
    subpixels (transmission 0.5); a black pixel retains none (transmission 0).
    """
    binary = np.asarray(binary_orig)
    if binary.ndim != 2 or binary.size == 0:
        raise ValueError("binary_orig must be a non-empty 2D array")
    recovered = np.asarray(recovered_img.convert("L"))
    expected_shape = (binary.shape[0] * 2, binary.shape[1] * 2)
    if recovered.shape != expected_shape:
        raise ValueError("recovered image dimensions must be exactly twice the source dimensions")

    white_mask = np.repeat(np.repeat(binary > 0, 2, axis=0), 2, axis=1)
    black_mask = ~white_mask
    recovered_white = recovered > 128
    t_white = float(np.mean(recovered_white[white_mask])) if np.any(white_mask) else 0.5
    t_black = float(np.mean(recovered_white[black_mask])) if np.any(black_mask) else 0.0
    return {
        "t_white": t_white,
        "t_black": t_black,
        "contrast_alpha": t_white - t_black,
    }
