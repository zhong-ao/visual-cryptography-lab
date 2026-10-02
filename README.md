# Visual Cryptography Lab: (2, 2) VCS Implementation and Evaluation

本项目针对 Moni Naor 与 Adi Shamir 提出的经典可视密码学方案（Visual Cryptography Scheme, VCS）进行了工程实现，并提供了一套基于信息论与统计特性的安全性量化评估工具。

## 1. 方案数学描述

针对二值图像（0: 黑色, 1: 白色），设定门限 (k, n) = (2, 2)，像素扩展度 m = 4。每个秘密像素扩展为一个 2x2 的子块，且每个子块严格包含 2 个黑色像素与 2 个白色像素。

### 基础矩阵 (Basis Matrices)
白色像素与黑色像素的分解模式分别由基础矩阵 S0 与 S1 决定：

```text
       [ 1  0  1  0 ]              [ 1  0  1  0 ]
S0  =  [            ]       S1  =  [            ]
       [ 1  0  1  0 ]              [ 0  1  0  1 ]
       (白色像素分解)               (黑色像素分解)