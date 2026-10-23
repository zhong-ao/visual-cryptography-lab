"""An image-based (2, 2) visual secret-sharing experiment."""

from __future__ import annotations

import hashlib
import io
import math
import zipfile

import numpy as np
import streamlit as st
from PIL import Image, ImageDraw

from secure_image_crypto import MAX_SOURCE_BYTES, normalize_image
from vc_core import (
    calculate_share_balance,
    calculate_theoretical_contrast,
    encrypt_visual_share,
    overlay_shares,
    preprocess_image,
)


def image_to_png_bytes(image: Image.Image) -> bytes:
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def make_demo_image(name: str, size: int = 192) -> Image.Image:
    image = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(image)
    scale = size / 144

    def points(items: list[tuple[int, int]]) -> list[tuple[int, int]]:
        return [(round(x * scale), round(y * scale)) for x, y in items]

    stroke = max(2, round(8 * scale))
    if name == "钥匙":
        draw.ellipse(points([(43, 15), (101, 73)]), fill=255)
        draw.ellipse(points([(59, 31), (85, 57)]), fill=0)
        draw.rounded_rectangle(points([(62, 59), (82, 116)]), radius=round(8 * scale), fill=255)
        draw.rounded_rectangle(points([(48, 98), (96, 121)]), radius=round(8 * scale), fill=255)
    elif name == "星星":
        vertices = []
        for index in range(10):
            angle = -np.pi / 2 + index * np.pi / 5
            radius = 58 if index % 2 == 0 else 25
            vertices.append(
                (round(72 + radius * np.cos(angle)), round(72 + radius * np.sin(angle)))
            )
        draw.polygon(points(vertices), fill=255)
    elif name == "笑脸":
        draw.ellipse(points([(18, 18), (126, 126)]), outline=255, width=stroke)
        draw.ellipse(points([(43, 49), (57, 66)]), fill=255)
        draw.ellipse(points([(87, 49), (101, 66)]), fill=255)
        draw.arc(points([(42, 42), (102, 104)]), start=20, end=160, fill=255, width=stroke)
    else:
        draw.polygon(
            points(
                [
                    (72, 119), (21, 69), (21, 48), (32, 30), (51, 25),
                    (72, 46), (93, 25), (112, 30), (123, 48), (123, 69),
                ]
            ),
            fill=255,
        )
    return image


def build_visual_package(share1: Image.Image, share2: Image.Image) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("share_1.png", image_to_png_bytes(share1))
        archive.writestr("share_2.png", image_to_png_bytes(share2))
        archive.writestr(
            "README.txt",
            "Visual secret sharing demo, (2, 2) threshold.\n"
            "Both shares are required to reveal the image.\n",
        )
    return output.getvalue()


st.title("视觉实验室", icon=":material/auto_awesome:")
st.write("一张秘密图，拆成两把视觉密钥。单独看像噪点，切到叠加视角，图案才会重新出现。")
st.divider()

st.subheader("01 · 准备一张秘密图")
st.caption("先挑一个图案，或上传自己的图片；然后调节黑白分界，生成两份密钥。")

source_kind = st.segmented_control(
    "图片从哪里来？",
    ["内置图案", "上传图片"],
    default="内置图案",
    key="visual_source_kind",
)

upload = None
demo_name = None
if source_kind == "内置图案":
    demo_name = st.pills(
        "挑一枚图案",
        ["钥匙", "星星", "笑脸", "爱心"],
        selection_mode="single",
        default="钥匙",
        key="visual_demo_name",
    )
else:
    upload = st.file_uploader(
        "选择一张 PNG 或 JPEG 图片",
        type=["png", "jpg", "jpeg"],
        help="点击文件选择器里的“浏览文件”选择图片。上限 10 MiB；透明区域会铺成白色。",
        key="visual_upload",
    )

setting_col, action_col = st.columns([1.35, 1], gap="large", vertical_alignment="bottom")
with setting_col:
    threshold = st.slider(
        "黑白分界",
        min_value=32,
        max_value=224,
        value=128,
        step=8,
        help="数值越高，越多像素会被分到黑色一侧。",
        key="visual_threshold",
    )
with action_col:
    generate = st.button(
        "拆成两份秘密",
        type="primary",
        icon=":material/auto_awesome:",
        width="stretch",
        key="generate_visual_shares",
    )

if source_kind == "内置图案":
    current_label = demo_name or "钥匙"
    current_bytes = image_to_png_bytes(make_demo_image(current_label))
    current_signature = ("demo", current_label, threshold)
elif upload is not None and upload.size <= MAX_SOURCE_BYTES:
    current_label = upload.name
    current_bytes = upload.getvalue()
    current_signature = ("upload", upload.name, hashlib.sha256(current_bytes).hexdigest(), threshold)
else:
    current_label = None
    current_bytes = None
    current_signature = None

if generate:
    st.session_state.pop("visual_share_result", None)
    if source_kind == "上传图片" and upload is None:
        st.error("先选择一张图片，再生成密钥。")
    elif source_kind == "上传图片" and upload is not None and upload.size > MAX_SOURCE_BYTES:
        st.error("图片文件不能超过 10 MiB，请压缩后再试。")
    else:
        try:
            if source_kind == "内置图案":
                source = make_demo_image(current_label or "钥匙")
            else:
                normalized = normalize_image(current_bytes or b"")
                source = Image.frombytes(
                    "RGB", (normalized.width, normalized.height), normalized.pixels
                )

            binary = preprocess_image(source, threshold=threshold, max_side=320)
            share1, share2 = encrypt_visual_share(binary)
            recovered = overlay_shares(share1, share2)
            source_for_display = Image.fromarray(binary * 255)
            contrast = calculate_theoretical_contrast(binary, recovered)
            balance1 = calculate_share_balance(binary, share1)
            balance2 = calculate_share_balance(binary, share2)
            st.session_state["visual_share_result"] = {
                "signature": current_signature,
                "label": current_label or "秘密图",
                "source": image_to_png_bytes(source_for_display),
                "share1": image_to_png_bytes(share1),
                "share2": image_to_png_bytes(share2),
                "recovered": image_to_png_bytes(recovered),
                "package": build_visual_package(share1, share2),
                "width": int(binary.shape[1]),
                "height": int(binary.shape[0]),
                "contrast": contrast["contrast_alpha"],
                "balance1": balance1["balance_gap"],
                "balance2": balance2["balance_gap"],
            }
        except (OSError, ValueError) as exc:
            st.error(str(exc))

result = st.session_state.get("visual_share_result")
if result and result.get("signature") == current_signature:
    st.divider()
    st.subheader("02 · 换个视角，发现秘密")
    st.caption("点击 A、B 或叠加，亲眼看看两份密钥如何一起显出图案。")

    observation = st.segmented_control(
        "观察方式",
        ["密钥 A", "密钥 B", "叠加还原"],
        default="叠加还原",
        key="visual_observation",
        label_visibility="collapsed",
    )
    observation = observation or "叠加还原"
    if observation == "密钥 A":
        shown_image = result["share1"]
        image_caption = "密钥 A · 单独看是一片随机纹理"
        observation_note = "这份密钥单独看不出秘密图案。"
    elif observation == "密钥 B":
        shown_image = result["share2"]
        image_caption = "密钥 B · 单独看也是随机纹理"
        observation_note = "换成另一份密钥，秘密仍然没有显形。"
    else:
        shown_image = result["recovered"]
        image_caption = "叠加还原 · 两份密钥合在一起，图案出现了"
        observation_note = "两份密钥叠加后，原来的黑白结构重新出现。"

    image_col, story_col = st.columns([1.35, 0.8], gap="large", vertical_alignment="center")
    with image_col:
        st.image(shown_image, caption=image_caption, width="stretch")
    with story_col:
        st.markdown("#### 现在你看到的是")
        st.write(observation_note)
        st.caption(
            f"{result['width']} × {result['height']} 像素 · "
            f"还原对比度 α {result['contrast']:.2f} · 需要两份密钥"
        )
        if st.toggle("对照处理后的黑白原图", key="reveal_visual_source"):
            st.image(result["source"], caption="用于拆分的黑白图案", width="stretch")

    st.markdown("#### 带走这次实验")
    download_cols = st.columns(3, gap="medium")
    with download_cols[0]:
        st.download_button(
            "下载密钥 A",
            data=result["share1"],
            file_name="share_1.png",
            mime="image/png",
            icon=":material/download:",
            width="stretch",
        )
    with download_cols[1]:
        st.download_button(
            "下载密钥 B",
            data=result["share2"],
            file_name="share_2.png",
            mime="image/png",
            icon=":material/download:",
            width="stretch",
        )
    with download_cols[2]:
        st.download_button(
            "下载完整实验包",
            data=result["package"],
            file_name="visual_secret_shares.zip",
            mime="application/zip",
            icon=":material/archive:",
            width="stretch",
        )

    with st.expander("为什么单份密钥的熵总是 1 bit？"):
        st.markdown(
            "这是这种 2×2 视觉秘密分享方案的固定性质：每个原始像素会展开成 2×2 子像素，"
            "单份密钥里黑白点各占一半，因此 p = 0.5，熵 H(p) = 1 bit。"
            "它不是随图片变化的安全评分；这个实验更适合观察单份密钥与叠加结果之间的视觉差异。"
        )
        gap1 = result["balance1"]
        gap2 = result["balance2"]
        gap1_text = f"{gap1:.2%}" if math.isfinite(gap1) else "无法计算"
        gap2_text = f"{gap2:.2%}" if math.isfinite(gap2) else "无法计算"
        st.caption(f"本次样本的白点比例偏差：密钥 A {gap1_text} · 密钥 B {gap2_text}")
elif result:
    st.divider()
    st.info("实验输入已经变化。确认图片和黑白分界后，重新拆分即可查看新结果。")
