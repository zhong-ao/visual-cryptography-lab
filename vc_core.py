"""
(2, 2) Visual Cryptography Scheme (Naor-Shamir) and Statistical Metrics
"""

import numpy as np
from PIL import Image


def preprocess_image(image: Image.Image, threshold: int = 128) -> np.ndarray:
    """图像灰度化与二值化处理 (0: 黑色, 1: 白色)"""
    gray = image.convert("L")
    return (np.array(gray) > threshold).astype(np.uint8)


def encrypt_visual_share(binary_img: np.ndarray) -> tuple[Image.Image, Image.Image]:
    """
    (2, 2) 门限可视密码分解
    像素扩展度 m = 4 (子块 2x2，每个子块包含 2 个黑色像素与 2 个白色像素)
    """
    h, w = binary_img.shape
    share1 = np.zeros((h * 2, w * 2), dtype=np.uint8)
    share2 = np.zeros((h * 2, w * 2), dtype=np.uint8)

    # 基础矩阵对应的 4 种 2x2 子块置换模式 (0: 黑色, 255: 白色)
    patterns = [
        np.array([[255, 0], [0, 255]], dtype=np.uint8),
        np.array([[0, 255], [255, 0]], dtype=np.uint8),
        np.array([[255, 255], [0, 0]], dtype=np.uint8),
        np.array([[0, 0], [255, 255]], dtype=np.uint8)
    ]

    for i in range(h):
        for j in range(w):
            base_p = patterns[np.random.randint(4)]
            share1[i * 2:(i + 1) * 2, j * 2:(j + 1) * 2] = base_p

            if binary_img[i, j] == 1:
                # 白色像素：两张 share 取相同子块
                share2[i * 2:(i + 1) * 2, j * 2:(j + 1) * 2] = base_p
            else:
                # 黑色像素：两张 share 取互补子块
                share2[i * 2:(i + 1) * 2, j * 2:(j + 1) * 2] = 255 - base_p

    return Image.fromarray(share1), Image.fromarray(share2)


def overlay_shares(share1_img: Image.Image, share2_img: Image.Image) -> Image.Image:
    """物理叠合模拟 (取像素灰度最小值，等价于光强吸收累加)"""
    arr1 = np.array(share1_img)
    arr2 = np.array(share2_img)
    return Image.fromarray(np.minimum(arr1, arr2))


def calculate_shannon_entropy(img_array: np.ndarray) -> float:
    """计算图像香农信息熵"""
    bin_data = (img_array > 128).astype(int).flatten()
    counts = np.bincount(bin_data, minlength=2)
    probs = counts / len(bin_data)
    probs = probs[probs > 0]
    return float(-np.sum(probs * np.log2(probs)))


def calculate_adjacent_correlation(
    img_array: np.ndarray, num_samples: int = 2000, direction: str = "horizontal"
) -> tuple[float, np.ndarray, np.ndarray]:
    """计算相邻像素的皮尔逊相关系数并返回采样分布点"""
    arr = img_array.astype(float)
    h, w = arr.shape

    if direction == "horizontal":
        x_coords = np.random.randint(0, h, num_samples)
        y_coords = np.random.randint(0, w - 1, num_samples)
        x = arr[x_coords, y_coords]
        y = arr[x_coords, y_coords + 1]
    else:
        x_coords = np.random.randint(0, h - 1, num_samples)
        y_coords = np.random.randint(0, w, num_samples)
        x = arr[x_coords, y_coords]
        y = arr[x_coords + 1, y_coords]

    # 添加轻微扰动便于散点可视化观察局部密度
    x_scatter = x + np.random.normal(0, 3, num_samples)
    y_scatter = y + np.random.normal(0, 3, num_samples)

    mean_x, mean_y = float(np.mean(x)), float(np.mean(y))
    cov_xy = float(np.sum((x - mean_x) * (y - mean_y)))
    var_prod = float(np.sqrt(np.sum((x - mean_x) ** 2) * np.sum((y - mean_y) ** 2)))

    r = 0.0 if var_prod == 0 else cov_xy / var_prod
    return float(r), x_scatter, y_scatter


def calculate_theoretical_contrast(binary_orig: np.ndarray, recovered_img: Image.Image) -> dict:
    """评估重构图像的白区透光率、黑区透光率及相对对比度 alpha"""
    orig_h, orig_w = binary_orig.shape
    rec_arr = np.array(recovered_img)

    white_mask = np.repeat(np.repeat(binary_orig == 1, 2, axis=0), 2, axis=1)
    black_mask = ~white_mask

    t_white = float(np.mean(rec_arr[white_mask] == 255)) if np.sum(white_mask) > 0 else 0.5
    t_black = float(np.mean(rec_arr[black_mask] == 255)) if np.sum(black_mask) > 0 else 0.0

    return {
        "t_white": t_white,
        "t_black": t_black,
        "contrast_alpha": t_white - t_black
    }