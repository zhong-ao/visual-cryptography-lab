import io
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import streamlit as st

from vc_core import (
    calculate_adjacent_correlation,
    calculate_shannon_entropy,
    calculate_theoretical_contrast,
    encrypt_visual_share,
    overlay_shares,
    preprocess_image,
)

st.set_page_config(page_title="Visual Cryptography Demo", layout="wide")

st.title("Visual Cryptography Scheme (VCS) 仿真与统计分析平台")
st.caption("实现模型: Naor-Shamir (2, 2) 门限可视密码学 | 像素扩展度 m = 4")

# 侧边栏配置
st.sidebar.subheader("图像预处理")
uploaded_file = st.sidebar.file_uploader("输入图像", type=["png", "jpg", "jpeg"])
threshold = st.sidebar.slider("二值化阈值", min_value=0, max_value=255, value=128)


def get_image_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


if uploaded_file is not None:
    raw_img = Image.open(uploaded_file)
    bin_array = preprocess_image(raw_img, threshold)

    col1, col2 = st.columns(2)

    with col1:
        st.write("##### 原始图像 (二值化)")
        st.image(bin_array * 255, width=320)

    re_encrypt = st.sidebar.button("重新生成分片")

    if (
        "current_file" not in st.session_state
        or st.session_state.current_file != uploaded_file.name
        or re_encrypt
    ):
        s1, s2 = encrypt_visual_share(bin_array)
        st.session_state.share1 = s1
        st.session_state.share2 = s2
        st.session_state.current_file = uploaded_file.name

    with col2:
        st.write("##### 分片图像 (Share 1 & Share 2)")
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            st.image(st.session_state.share1, caption="Share 1", use_container_width=True)
            st.download_button("导出 Share 1", get_image_bytes(st.session_state.share1), "share1.png")
        with sub_col2:
            st.image(st.session_state.share2, caption="Share 2", use_container_width=True)
            st.download_button("导出 Share 2", get_image_bytes(st.session_state.share2), "share2.png")

    st.divider()

    # 叠合重构
    st.write("##### 重构图像 (Physical Overlay)")
    recovered_img = overlay_shares(st.session_state.share1, st.session_state.share2)
    st.image(recovered_img, caption="叠合解码结果 (Contrast = 50%)", width=420)

    # 统计与安全指标
    st.divider()
    st.write("##### 密码学统计特性与安全评估")

    entropy_orig = calculate_shannon_entropy(bin_array * 255)
    entropy_s1 = calculate_shannon_entropy(np.array(st.session_state.share1))

    r_orig, orig_x, orig_y = calculate_adjacent_correlation(bin_array * 255, num_samples=2000)
    r_s1, s1_x, s1_y = calculate_adjacent_correlation(np.array(st.session_state.share1), num_samples=2000)

    stats = calculate_theoretical_contrast(bin_array, recovered_img)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Share 1 信息熵", f"{entropy_s1:.4f} bit", help="理论最大熵为 1.0000 bit")
    m2.metric("Share 1 像素相关性", f"{r_s1:.4f}", help="越趋近于 0 表明空间独立性越好")
    m3.metric("原图像素相关性", f"{r_orig:.4f}")
    m4.metric("相对对比度 α", f"{stats['contrast_alpha']:.2f}", help="Naor-Shamir 理论值为 0.50")

    # 散点图
    fig, (ax_orig, ax_share) = plt.subplots(1, 2, figsize=(9, 3.8))

    ax_orig.scatter(orig_x, orig_y, c="#2c3e50", s=6, alpha=0.35)
    ax_orig.set_title(f"Original Image (r = {r_orig:.3f})", fontsize=10)
    ax_orig.set_xlabel("Pixel (x, y)")
    ax_orig.set_ylabel("Pixel (x+1, y)")
    ax_orig.set_xlim(-15, 270)
    ax_orig.set_ylim(-15, 270)
    ax_orig.grid(True, linestyle=":", alpha=0.6)

    ax_share.scatter(s1_x, s1_y, c="#c0392b", s=6, alpha=0.35)
    ax_share.set_title(f"Share 1 (r = {r_s1:.3f})", fontsize=10)
    ax_share.set_xlabel("Pixel (x, y)")
    ax_share.set_ylabel("Pixel (x+1, y)")
    ax_share.set_xlim(-15, 270)
    ax_share.set_ylim(-15, 270)
    ax_share.grid(True, linestyle=":", alpha=0.6)

    st.pyplot(fig)
else:
    st.info("请在左侧侧边栏上传测试图像。")