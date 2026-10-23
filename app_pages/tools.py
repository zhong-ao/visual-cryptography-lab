"""Practical text and image cryptography utilities."""

from __future__ import annotations

import hashlib
import io

import streamlit as st
from cryptography.exceptions import InvalidTag
from PIL import Image

from cipher_core import caesar_cipher, morse_decode, morse_encode, vigenere_cipher
from secure_image_crypto import (
    HEADER_SIZE,
    MAX_CONTAINER_BYTES,
    MAX_SOURCE_BYTES,
    TAG_SIZE,
    InvalidContainerError,
    PasswordPolicyError as ImagePasswordPolicyError,
    decrypt_container,
    encrypt_pixels,
    normalize_image,
)
from secure_text_crypto import (
    InvalidTextPackageError,
    PasswordPolicyError,
    decrypt_text,
    encrypt_text,
)


def image_to_png_bytes(image: Image.Image) -> bytes:
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


st.title("密码工具箱")
st.caption("经典密码用来学习，现代加密用来保护便笺和图片。所有操作由当前运行此应用的服务器处理。")

tool = st.segmented_control(
    "选择工具",
    ["经典密码", "安全便笺", "图片保险箱", "SHA-256"],
    default="经典密码",
    key="tool_mode",
    width="stretch",
)

if tool == "经典密码":
    st.subheader("把文字变成另一种样子")
    cipher = st.segmented_control(
        "算法",
        ["凯撒移位", "维吉尼亚", "摩斯电码"],
        default="凯撒移位",
        key="classic_cipher",
    )
    direction = st.segmented_control(
        "方向",
        ["加密", "解密"],
        default="加密",
        key="classic_direction",
    )
    with st.form("classic_cipher_form"):
        source = st.text_area("输入文字", height=150, placeholder="输入要处理的文本")
        shift = 3
        key = "LEMON"
        if cipher == "凯撒移位":
            shift = st.slider("位移量", min_value=1, max_value=25, value=3)
        elif cipher == "维吉尼亚":
            key = st.text_input("关键词", value="LEMON", help="密钥只使用英文字母。")
        else:
            st.caption("摩斯电码支持英文字母和数字；用空格分隔字母，用 / 分隔单词。")
        run_classic = st.form_submit_button(
            f"{direction}文字",
            type="primary",
            icon=":material/transform:",
            width="stretch",
        )

    if run_classic:
        st.session_state.pop("classic_result", None)
        try:
            if cipher == "凯撒移位":
                result = caesar_cipher(source, shift if direction == "加密" else -shift)
            elif cipher == "维吉尼亚":
                result = vigenere_cipher(source, key, decrypt=direction == "解密")
            elif direction == "加密":
                result = morse_encode(source)
            else:
                result = morse_decode(source)
            st.session_state["classic_result"] = {
                "cipher": cipher,
                "direction": direction,
                "result": result,
            }
        except ValueError as exc:
            st.error(str(exc))

    classic_result = st.session_state.get("classic_result")
    if classic_result and classic_result["cipher"] == cipher and classic_result["direction"] == direction:
        with st.container(border=True):
            st.markdown("**处理结果**")
            st.code(classic_result["result"], language=None)
            st.download_button(
                "下载结果文本",
                data=classic_result["result"],
                file_name="cipher_result.txt",
                mime="text/plain",
                icon=":material/download:",
            )
    st.warning("凯撒、维吉尼亚和摩斯码只适合学习与趣味交流，不要用来保护真实隐私。", icon=":material/info:")

elif tool == "安全便笺":
    st.subheader("给一段文字加上口令锁")
    action = st.segmented_control(
        "便笺操作",
        ["加密", "解密"],
        default="加密",
        key="note_action",
    )
    if action == "加密":
        with st.form("encrypt_note_form"):
            plaintext = st.text_area("要加密的便笺", height=180, placeholder="只加密你愿意提交到当前应用服务器的内容")
            password = st.text_input(
                "设置口令",
                type="password",
                max_chars=256,
                help="至少 12 个字符；建议用容易记但不常见的长口令。",
            )
            confirm = st.text_input("再输一次口令", type="password", max_chars=256)
            encrypt_note = st.form_submit_button(
                "生成加密便笺",
                type="primary",
                icon=":material/encrypted:",
                width="stretch",
            )

        if encrypt_note:
            st.session_state.pop("note_result", None)
            if password != confirm:
                st.error("两次口令不一致。")
            else:
                try:
                    token = encrypt_text(plaintext, password)
                    st.session_state["note_result"] = {"action": "加密", "value": token}
                except (PasswordPolicyError, ValueError) as exc:
                    st.error(str(exc))

    else:
        with st.form("decrypt_note_form"):
            token = st.text_area(
                "粘贴 CLTEXT1 加密便笺",
                height=180,
                placeholder="粘贴以 CLTEXT1: 开头的内容",
            )
            password = st.text_input("解密口令", type="password", max_chars=256)
            decrypt_note = st.form_submit_button(
                "验证并解密",
                type="primary",
                icon=":material/lock_open:",
                width="stretch",
            )

        if decrypt_note:
            st.session_state.pop("note_result", None)
            try:
                plaintext = decrypt_text(token, password)
                st.session_state["note_result"] = {"action": "解密", "value": plaintext}
            except InvalidTag:
                st.error("认证失败：口令不正确，或加密便笺已被修改。没有输出明文。")
            except (InvalidTextPackageError, ValueError) as exc:
                st.error(str(exc))

    note_result = st.session_state.get("note_result")
    if note_result and note_result["action"] == action:
        with st.container(border=True):
            if action == "加密":
                st.markdown("**加密便笺**")
                st.code(note_result["value"], language=None)
                st.download_button(
                    "下载 .clnote 文件",
                    data=note_result["value"],
                    file_name="private_note.clnote",
                    mime="text/plain",
                    icon=":material/download:",
                )
            else:
                st.success("认证通过，明文已还原。")
                st.code(note_result["value"], language=None)

    with st.expander("便笺加密用了什么？"):
        st.markdown(
            "口令经 **Scrypt** 派生密钥，内容再由 **AES-256-GCM** 加密并附带认证标签。"
            "口令不会写进 `.clnote` 文件；如果口令遗失，文件无法还原。"
        )

elif tool == "图片保险箱":
    st.subheader("把图片装进可解锁的文件")
    action = st.segmented_control(
        "图片操作",
        ["加密图片", "解密图片"],
        default="加密图片",
        key="image_vault_action",
    )
    if action == "加密图片":
        with st.form("encrypt_image_form"):
            upload = st.file_uploader(
                "选择 PNG 或 JPEG",
                type=["png", "jpg", "jpeg"],
                help="单张图片最多 10 MiB，最多 800 万像素。",
            )
            password = st.text_input("设置图片口令", type="password", max_chars=256)
            confirm = st.text_input("再次输入图片口令", type="password", max_chars=256)
            encrypt_image = st.form_submit_button(
                "加密图片",
                type="primary",
                icon=":material/encrypted:",
                width="stretch",
            )

        if encrypt_image:
            st.session_state.pop("image_vault_result", None)
            if upload is None:
                st.error("先选择一张图片。")
            elif password != confirm:
                st.error("两次口令不一致。")
            elif upload.size > MAX_SOURCE_BYTES:
                st.error("图片文件超过 10 MiB。")
            else:
                try:
                    normalized = normalize_image(upload.getvalue())
                    container = encrypt_pixels(
                        normalized.pixels,
                        normalized.width,
                        normalized.height,
                        password,
                    )
                    preview = Image.frombytes(
                        "RGB", (normalized.width, normalized.height), normalized.pixels
                    )
                    st.session_state["image_vault_result"] = {
                        "action": action,
                        "name": upload.name.rsplit(".", 1)[0],
                        "container": container,
                        "preview": image_to_png_bytes(preview),
                        "width": normalized.width,
                        "height": normalized.height,
                    }
                except (ImagePasswordPolicyError, ValueError) as exc:
                    st.error(str(exc))

    else:
        with st.form("decrypt_image_form"):
            upload = st.file_uploader(
                "选择 .vclab 图片包",
                type=["vclab"],
                help="包内带有图片尺寸、随机 salt、nonce 和认证密文。",
            )
            password = st.text_input("图片口令", type="password", max_chars=256)
            decrypt_image = st.form_submit_button(
                "验证并解密",
                type="primary",
                icon=":material/lock_open:",
                width="stretch",
            )

        if decrypt_image:
            st.session_state.pop("image_vault_result", None)
            if upload is None:
                st.error("先选择一个 `.vclab` 文件。")
            elif upload.size > MAX_CONTAINER_BYTES:
                st.error("加密包超过 32 MiB。")
            else:
                try:
                    container = upload.getvalue()
                    decrypted = decrypt_container(container, password)
                    st.session_state["image_vault_result"] = {
                        "action": action,
                        "image": image_to_png_bytes(decrypted.image),
                        "width": decrypted.image.width,
                        "height": decrypted.image.height,
                    }
                except InvalidTag:
                    st.error("认证失败：口令不正确，或图片包被修改。没有输出图片。")
                except (InvalidContainerError, ValueError) as exc:
                    st.error(str(exc))

    image_result = st.session_state.get("image_vault_result")
    if image_result and image_result["action"] == action:
        with st.container(border=True):
            if action == "加密图片":
                left, right = st.columns([1, 1.2], gap="large")
                with left:
                    st.image(image_result["preview"], caption="加密前预览", width="stretch")
                with right:
                    st.success(f"已生成认证加密包 · {image_result['width']} × {image_result['height']}")
                    st.download_button(
                        "下载 .vclab 文件",
                        data=image_result["container"],
                        file_name=f"{image_result['name']}.vclab",
                        mime="application/octet-stream",
                        type="primary",
                        icon=":material/download:",
                    )
            else:
                st.success(f"认证通过 · {image_result['width']} × {image_result['height']}")
                st.image(image_result["image"], caption="已还原的图片", width="stretch")
                st.download_button(
                    "下载还原图片 PNG",
                    data=image_result["image"],
                    file_name="decrypted_image.png",
                    mime="image/png",
                    icon=":material/download:",
                )

    with st.expander("图片保险箱说明"):
        st.markdown(
            "图片统一转换为 RGB 像素；尺寸信息可见，EXIF 元数据不会保留。"
            "每次加密生成新 salt 和 nonce。发生篡改或口令错误时，认证失败，不输出部分明文。"
        )

else:
    st.subheader("生成一枚可核对的数字指纹")
    st.caption("SHA-256 可检查内容是否一致；它是哈希，不是加密，也不能从摘要还原原文。")
    with st.form("sha256_form"):
        source = st.text_area("要计算摘要的文本", height=160)
        expected = st.text_input("可选：粘贴预期摘要进行比对", max_chars=64)
        hash_text = st.form_submit_button(
            "生成 SHA-256 指纹",
            type="primary",
            icon=":material/fingerprint:",
            width="stretch",
        )

    if hash_text:
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
        st.session_state["sha256_result"] = {
            "digest": digest,
            "matches": bool(expected.strip()) and expected.strip().casefold() == digest,
            "was_compared": bool(expected.strip()),
        }
    digest_result = st.session_state.get("sha256_result")
    if digest_result:
        with st.container(border=True):
            st.markdown("**SHA-256 · UTF-8 输入**")
            st.code(digest_result["digest"], language=None)
            if digest_result["was_compared"]:
                if digest_result["matches"]:
                    st.success("摘要一致，两个输入对应相同的 SHA-256 指纹。")
                else:
                    st.warning("摘要不同；文本或预期指纹至少有一项不一致。")
            st.download_button(
                "下载摘要文本",
                data=digest_result["digest"],
                file_name="sha256.txt",
                mime="text/plain",
                icon=":material/download:",
            )
