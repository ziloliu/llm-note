---
title: "USART1字符串收发"
category: "STM32/USART"
tags: [USART1, 字符串, SendString, ReceiveString, IDLE]
abstract: "USART1发送和接收字符串的实现方法，包括SendString函数和ReceiveString的两种结束判断方式"
source: "原创"
update_time: 2026-05-31
status: 完成
type: 实操
---

## 一句话定义

USART1发送字符串通过循环调用SendChar实现，接收字符串需要判断结束条件，常用IDLE空闲帧检测或约定长度方式。

## 核心内容

### 函数声明（usart.h）

```c
// 发送字符串（已知长度）
void USART1_SendString(uint8_t *str, uint16_t size);

// 接收字符串（未知长度，通过指针返回接收个数）
void USART1_ReceiveString(uint8_t *buffer, uint8_t *size);
```

**参数说明：**

| 函数 | 参数 | 说明 |
|------|------|------|
| SendString | `uint8_t *str` | 待发送字符串的首地址（指针） |
| SendString | `uint16_t size` | 发送字符的个数 |
| ReceiveString | `uint8_t *buffer` | 接收缓冲区（数组/指针） |
| ReceiveString | `uint8_t *size` | 指针，用于回传实际接收到的字符个数 |

> 接收函数使用指针参数回传个数，因为接收时无法预知对方发送多少字符，无法通过返回值同时返回数据和个数。

### 发送字符串实现

**代码：**
```c
void USART1_SendString(uint8_t *str, uint16_t size)
{
    for (uint16_t i = 0; i < size; i++)
    {
        USART1_SendChar(str[i]);   // 逐个字符调用单字符发送函数
    }
}
```

**执行流程：**
```
for 循环遍历字符串数组
    ↓ 每次循环
USART1_SendChar(str[i])
    ↓ 内部逻辑
while(SR.TXE == 0);   // 等待发送缓冲区空
DR = str[i];           // 写入字符
    ↓ 循环结束
所有字符发送完毕
```

### 主函数测试：发送字符串

```c
#include "stm32f10x.h"
#include "usart.h"
#include "string.h"

int main(void)
{
    USART1_Init();

    // 定义字符串（含 '\0' 结束符）
    uint8_t *str = "Hello World";

    // strlen 计算长度（不含 '\0'），需强制类型转换避免警告
    USART1_SendString(str, (uint16_t)strlen((char *)str));

    while (1)
    {
    }
}
```

**注意事项：**

| 注意点 | 说明 |
|--------|------|
| `strlen` 返回值类型 | `size_t`（无符号整型），传参时转为 `uint16_t` 避免类型不匹配警告 |
| `strlen` 参数类型 | 要求 `const char *`，传入 `uint8_t *` 需强转为 `(char *)` |
| 字符串长度 | `strlen` 返回的长度**不含** `\0` 结束符，若需发送换行等需手动追加 |

**预期结果：** 串口助手收到：`Hello World`

### 接收字符串的思路

**核心问题：**
- 发送方发送的字符数量**未知**
- 无法提前知道接收多少个字符
- 需要一种方式判断"接收完毕"

**两种判断接收结束的方式：**

| 方式 | 说明 |
|------|------|
| **约定长度** | 收发双方预先约定发送多少个字符，接收端按个数接收 |
| **检测空闲帧** | 检测 SR 寄存器的 **IDLE** 标志位，线路空闲一帧长度则判定数据发送完毕 |

**检测 IDLE 标志位：**
```
数据持续到达 → RXNE 反复置 1 → 逐个读取 DR
    ↓ 数据发送完毕，线路持续空闲
IDLE 置 1 → 判定一串数据接收结束
```

> IDLE 检测方式适用于变长数据（如字符串），是更通用的接收结束判断方法。

### 完整代码结构

```
usart.h
├── USART1_Init()                // 初始化
├── USART1_SendChar()            // 发送单个字符（轮询 TXE）
├── USART1_ReceiveChar()         // 接收单个字符（轮询 RXNE）
├── USART1_SendString()          // 发送字符串（循环调用 SendChar）
└── USART1_ReceiveString()       // 接收字符串（循环调用 ReceiveChar + 结束判断）

usart.c
└── 以上所有函数的实现

main.c
└── 初始化 + 功能测试
```

### 关键扩展点

| 扩展方向 | 说明 |
|----------|------|
| 接收字符串结束判断 | 可使用 IDLE 空闲帧检测，或约定固定长度 |
| printf 重定向 | 可重写 `fputc` 函数，将 `printf` 输出重定向到 USART1 |
| 中断方式收发 | 接收使用 RXNE 中断，避免轮询阻塞 CPU |
| DMA 方式 | 大量数据收发时使用 DMA 通道，进一步释放 CPU |

## 注意事项 & 踩坑

- 发送字符串需要知道长度，通常使用strlen计算
- strlen返回值类型是size_t，需要类型转换
- 接收字符串需要判断结束条件，IDLE检测是通用方案
- 接收函数使用指针参数返回接收个数

## 相关笔记

- [[USART1轮询方式收发]]
- [[USART1接收字符串实现]]
- [[IDLE标志位处理与改进]]

## 参考来源

- STM32F103开发板实验教程
