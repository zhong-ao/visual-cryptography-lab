# 密码局 Cipher Arcade

**Play to crack. Build to protect.**

An interactive cryptography arcade with progressive puzzles, practical authenticated-encryption tools, and a visual secret-sharing lab.

一个把密码学变成可玩的闯关和可用工具的 Streamlit 项目。你可以从一条短密文开始，逐关学替换密码、摩斯电码、哈希、认证加密和 nonce；也可以用同一套应用加密便笺或图片，或者亲手把秘密图像拆成两份。

项目面向密码学课程学习和复试展示，重点是让每个操作都能回答三个问题：我在做什么、为什么有效、它有什么限制。

## 先怎么玩

启动后会进入 **开始闯关**：

1. 阅读任务简报和密文。
2. 输入还原后的明文，或选择你的判断。
3. 提交后拿到积分和原理解释；答错不扣分，提示会少拿一些积分。
4. 完成一关后解锁下一关。当前分数与连胜只保存在这个浏览器会话里。

接着可以打开 **密码工具**：

- **经典密码**：凯撒、维吉尼亚和摩斯码的加解密。
- **安全便笺**：用口令加密文本，下载 `.clnote`，之后粘贴文件内容并验证解密。
- **图片保险箱**：用口令加密 PNG/JPEG，下载 `.vclab`，再上传还原图片。
- **SHA-256**：生成文本摘要，并可与已有摘要比对。

在 **视觉实验室** 上传一张图片或选择内置图案。程序会把图像拆成 Share 1 和 Share 2；单独看时像随机纹理，叠加后才显出秘密。你可以下载单份份额，也可以下载双份实验包。

## 密码学设计

### 便笺和图片加密

- 口令通过 **Scrypt** 派生 256-bit 密钥，参数为 `n=2^14, r=8, p=1`。
- 内容使用 **AES-256-GCM** 加密；包头作为附加认证数据，篡改包头或密文都会导致认证失败。
- 每次加密生成新的随机 salt 和 96-bit nonce。nonce 不需要保密，但同一把 AES-GCM 密钥下不得重复使用。
- 解密失败时拒绝输出明文或图片。

便笺封装带有 `CLTEXT1:` 版本前缀；图片包带有 `.vclab` 扩展名。图片先统一转成 RGB 像素；尺寸可见，EXIF 不保留，透明区域合成到白色背景。图片上限为 10 MiB、800 万像素。

### 视觉秘密分享

这是一个 `(2, 2)` 阈值方案：两份都在场才能看到秘密。每个源像素展开成一个 2×2 子像素块，单份块严格包含两个黑点和两个白点，所以单份二值熵固定为 `H(0.5)=1 bit`。这个值是构造性质，不是随图片变化的安全评分；秘密保存在两份图案之间的对应关系里。

### 学习提醒

凯撒、维吉尼亚和摩斯码是教学工具，不能保护真实隐私。SHA-256 是摘要，不是加密；普通快速哈希也不适合直接存储用户口令。AES-GCM 和 Scrypt 的代码用于学习与小型本地演示，不是经过审计的专业文件保险箱。

## 本地运行

需要 Python 3.10 或更高版本。

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

macOS / Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

应用不调用外部 API。若部署到公开服务器，口令、便笺和图片会经过该服务器处理；请使用演示数据，不要输入真实敏感内容。应用不会把密文放进外部存储，但会在当前 Streamlit 会话中暂存界面结果。

## 目录结构

```text
app.py                  页面路由、进度面板和主题入口
app_pages/mission.py    闯关、提示、积分与原理讲解
app_pages/tools.py      经典密码、便笺、图片与哈希工具
app_pages/lab.py        视觉秘密分享互动实验
cipher_core.py          教学密码函数和任务卡片
secure_text_crypto.py   便笺的 Scrypt + AES-GCM 封装
secure_image_crypto.py  图片的 Scrypt + AES-GCM 封装
vc_core.py              视觉分享算法、预处理与统计
.streamlit/config.toml  应用主题和上传限制
```

## 复试讨论题

1. 为什么凯撒密码可以直接穷举？维吉尼亚如何改变字母频率特征？
2. 哈希和加密的目标有什么不同？为什么弱口令哈希仍可被字典搜索？
3. AES-GCM 的认证标签验证失败后，为什么不能继续输出“尽量解出来”的明文？
4. nonce 为什么可以公开？同一密钥下重复使用 nonce 会破坏什么安全性质？
5. `(2, 2)` 视觉秘密分享的单份熵为何固定为 1 bit？秘密信息实际由什么承载？

## 参考资料

- [Streamlit multipage apps](https://docs.streamlit.io/develop/concepts/multipage-apps)
- [AES-GCM API](https://cryptography.io/en/latest/hazmat/primitives/aead/)
- [Scrypt API](https://cryptography.io/en/latest/hazmat/primitives/key-derivation-functions/#scrypt)
