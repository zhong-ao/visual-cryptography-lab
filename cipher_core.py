"""Small, auditable cipher helpers and the Cipher Arcade mission deck."""

from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Mission:
    id: str
    title: str
    category: str
    story: str
    prompt: str
    ciphertext: str
    answer: str
    hint: str
    lesson: str
    points: int
    choices: tuple[str, ...] = ()

    @property
    def is_multiple_choice(self) -> bool:
        return bool(self.choices)


MORSE_CODE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".",
    "F": "..-.", "G": "--.", "H": "....", "I": "..", "J": ".---",
    "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---",
    "P": ".--.", "Q": "--.-", "R": ".-.", "S": "...", "T": "-",
    "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--",
    "Z": "--..", "0": "-----", "1": ".----", "2": "..---",
    "3": "...--", "4": "....-", "5": ".....", "6": "-....",
    "7": "--...", "8": "---..", "9": "----.",
}
_MORSE_REVERSE = {code: letter for letter, code in MORSE_CODE.items()}


def caesar_cipher(text: str, shift: int) -> str:
    """Shift ASCII letters while preserving case, punctuation, and spacing."""
    shift %= 26
    output: list[str] = []
    for char in text:
        if "A" <= char <= "Z":
            output.append(chr((ord(char) - ord("A") + shift) % 26 + ord("A")))
        elif "a" <= char <= "z":
            output.append(chr((ord(char) - ord("a") + shift) % 26 + ord("a")))
        else:
            output.append(char)
    return "".join(output)


def vigenere_cipher(text: str, key: str, *, decrypt: bool = False) -> str:
    """Apply Vigenere to ASCII letters; punctuation does not consume the key."""
    key_values = [
        ord(char.upper()) - ord("A")
        for char in key
        if "A" <= char <= "Z" or "a" <= char <= "z"
    ]
    if not key_values:
        raise ValueError("密钥至少要包含一个英文字母。")

    output: list[str] = []
    key_index = 0
    direction = -1 if decrypt else 1
    for char in text:
        if "A" <= char <= "Z":
            shift = direction * key_values[key_index % len(key_values)]
            output.append(chr((ord(char) - ord("A") + shift) % 26 + ord("A")))
            key_index += 1
        elif "a" <= char <= "z":
            shift = direction * key_values[key_index % len(key_values)]
            output.append(chr((ord(char) - ord("a") + shift) % 26 + ord("a")))
            key_index += 1
        else:
            output.append(char)
    return "".join(output)


def morse_encode(text: str) -> str:
    """Encode letters and digits; use / to keep word boundaries readable."""
    words: list[str] = []
    for word in text.upper().split():
        try:
            words.append(" ".join(MORSE_CODE[char] for char in word))
        except KeyError as exc:
            raise ValueError(f"摩斯电码暂不支持字符：{exc.args[0]}") from exc
    return " / ".join(words)


def morse_decode(code: str) -> str:
    """Decode whitespace-separated Morse symbols; / separates words."""
    words: list[str] = []
    for word in code.strip().split("/"):
        letters: list[str] = []
        for symbol in word.split():
            try:
                letters.append(_MORSE_REVERSE[symbol])
            except KeyError as exc:
                raise ValueError(f"无法识别这组摩斯符号：{symbol}") from exc
        if letters:
            words.append("".join(letters))
    return " ".join(words)


def normalize_answer(answer: str) -> str:
    """Ignore spacing and punctuation when checking a plaintext guess."""
    normalized = unicodedata.normalize("NFKC", answer).casefold()
    return "".join(char for char in normalized if char.isalnum())


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_missions() -> tuple[Mission, ...]:
    hash_target = sha256_text("papercrane")
    return (
        Mission(
            id="shift-01",
            title="凌晨电台",
            category="凯撒移位 · 入门",
            story="凌晨 02:14，旧电台截获了一句留言。字母似乎被统一推开了几格。",
            prompt="还原英文明文。空格可以保留，也可以不写。",
            ciphertext="PHHW PH DW WKH OLEUDUB",
            answer="MEET ME AT THE LIBRARY",
            hint="每个字母向后移了 3 位；解码时把它向前移回来。",
            lesson="凯撒密码只有 26 种位移，穷举很快就能破解。它适合讲解替换密码，不适合保护真实秘密。",
            points=100,
        ),
        Mission(
            id="morse-02",
            title="灯塔回声",
            category="摩斯电码 · 观察",
            story="海岸灯塔亮起了一串长短闪光。斜线把单词分开，点和划各代表一个字母。",
            prompt="把摩斯电码翻译成英文。",
            ciphertext="-.-. --- -.. . / .. ... / .--. --- .-- . .-.",
            answer="CODE IS POWER",
            hint="开头四个符号是 C、O、D、E；可在工具箱里试着逐个翻译。",
            lesson="摩斯码是编码，不是加密：任何知道对应表的人都能还原内容。编码解决表示方式，加密才试图限制谁能读取。",
            points=120,
        ),
        Mission(
            id="vigenere-03",
            title="双层密钥",
            category="维吉尼亚 · 进阶",
            story="这封信使用了一个会循环的关键词。密钥已经从信封背面找到了。",
            prompt="用密钥 `LEMON` 解开密文。",
            ciphertext="LXFOPV EF RNHR",
            answer="ATTACK AT DAWN",
            hint="把 LEMON 重复到和字母一样长；每个密文字母都要减去对应的密钥位移。",
            lesson="维吉尼亚让不同位置使用不同位移，比单一凯撒更难直接看出字母频率；重复密钥仍会留下可分析的周期结构。",
            points=150,
        ),
        Mission(
            id="hash-04",
            title="摘要寻人",
            category="SHA-256 · 候选搜索",
            story="档案员留下了四个可能的口令。你的任务是找出哪个候选词会生成这枚指纹。",
            prompt="选出生成下方 SHA-256 摘要的原文。",
            ciphertext=hash_target,
            answer="papercrane",
            choices=("paper crane", "paper-crane", "papercrane", "paperplanes"),
            hint="摘要不能像密文那样直接解密；只能把候选逐个计算，再比较摘要。",
            lesson="哈希是单向摘要，不是加密。口令哈希还需要盐和专门的慢速 KDF；候选太弱时，攻击者仍可字典枚举。",
            points=180,
        ),
        Mission(
            id="tag-05",
            title="篡改现场",
            category="AES-GCM · 完整性",
            story="传输途中，密文有一个比特发生了改变。接收端拿到 AES-GCM 标签后应该怎么做？",
            prompt="选择最安全的接收行为。",
            ciphertext="密文已变化 · 认证标签不匹配",
            answer="认证失败，拒绝输出明文",
            choices=("忽略标签，尽量解出内容", "认证失败，拒绝输出明文", "把标签当作额外的图片字节"),
            hint="认证加密把保密性和篡改检测放在同一个解密验证流程里。",
            lesson="AEAD 解密认证失败时应拒绝明文。把失败结果当成部分可信数据会破坏完整性保障。",
            points=200,
        ),
        Mission(
            id="nonce-06",
            title="Nonce 规则",
            category="AES-GCM · 协议判断",
            story="工程师为了方便，准备在同一把密钥下重复使用一个 GCM nonce。你需要拦下这次发布。",
            prompt="选择应写进代码审查意见里的规则。",
            ciphertext="同一密钥 K · nonce N · 两条消息",
            answer="同一密钥下绝不重复使用 nonce",
            choices=("nonce 可以固定，只要明文不同", "同一密钥下绝不重复使用 nonce", "nonce 必须保密，传输时不能发送"),
            hint="nonce 通常不是秘密；危险的是同一密钥下重复使用它。",
            lesson="GCM nonce 不需要保密，但必须按方案保证唯一。重复使用会破坏安全性，因此工程上常用随机 nonce 并控制使用量，或设计可靠计数器。",
            points=220,
        ),
    )
