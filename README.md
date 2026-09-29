# Visual Cryptography Lab: (2, 2) VCS Implementation and Evaluation

本项目针对 Moni Naor 与 Adi Shamir 在 EUROCRYPT '94 提出的经典可视密码学方案（Visual Cryptography Scheme, VCS）进行了实现，并提供了一套基于统计学与信息论的安全评估工具。

## 1. 方案数学描述

针对二值图像（0: 黑色, 1: 白色），设门限为 $(k, n) = (2, 2)$，像素扩展度 $m = 4$。每个像素对应一个 $2 \times 2$ 的子块，包含 2 个黑色像素与 2 个白色像素。

* **基础矩阵（Basis Matrices）**:
  $$S_0 = \begin{bmatrix} 1 & 0 & 1 & 0 \\ 1 & 0 & 1 & 0 \end{bmatrix}, \quad S_1 = \begin{bmatrix} 1 & 0 & 1 & 0 \\ 0 & 1 & 0 & 1 \end{bmatrix}$$
  * 当秘密像素为白色时，从 $S_0$ 的列置换矩阵集合中等概率随机选取一行分配给 Share 1，另一行分配给 Share 2；
  * 当秘密像素为黑色时，从 $S_1$ 的列置换矩阵集合中选取。
* **物理叠加解码**:
  通过两张透明胶片的空间对齐叠合（布尔 OR 操作）实现无计算解码。白像素重构透光率为 $1/2$，黑像素重构透光率为 $0$，相对对比度 $\alpha = 1/2$。

## 2. 统计与安全性评估结果

在典型二值文本与线条图像测试下的实验指标：

| 评估维度 | 指标项 | 原图 | 单分片 (Share 1) | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| **信息泄露** | 香农信息熵 $H(X)$ | $\approx 0.45\text{ bit}$ | **$1.0000\text{ bit}$** | 达到二值随机变量最大熵，满足信息论安全 |
| **空间统计** | 水平相邻像素相关性 $r$ | **$0.875$** | **$-0.012$** | 空间自相关性被有效破坏，散点呈各向同性分布 |
| **重构性能** | 对比度 $\alpha$ | - | **$0.50$** | 实测值与理论值完全一致 |

## 3. 运行环境与安装

### 依赖项
* Python 3.10+
* 依赖库见 `requirements.txt` (`numpy`, `Pillow`, `streamlit`, `matplotlib`)

### 启动命令
```bash
pip install -r requirements.txt
streamlit run app.py