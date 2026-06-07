---
title: "USART1初始化代码实现"
category: "STM32/USART"
tags: [USART1, 初始化, GPIO, 时钟, 代码]
abstract: "USART1寄存器方式初始化的完整代码实现，包括时钟、GPIO、波特率、使能配置"
source: "原创"
update_time: 2026-05-31
status: 完成
type: 实操
---

## 一句话定义

USART1初始化包括5个步骤：开启时钟、配置GPIO（PA9复用推挽、PA10浮空输入）、设置波特率BRR=0x271、使能UE+TE+RE。

## 核心内容

### 工程结构

```
Project/
├── Hardware/
│   ├── LED/          (已有，保留)
│   ├── Key/          (已有，保留)
│   └── USART/        (新建)
│       ├── usart.c
│       └── usart.h
├── System/
├── User/
└── Startup/
```

**Keil 工程配置：**

| 配置项 | 操作 |
|--------|------|
| 添加 Group | 新建 "Hardware_USART" 组，添加 usart.c |
| Include Path | 添加 `Hardware/USART` 路径 |
| Debug 设置 | 勾选 "Reset and Run"，取消 "Load Application at Startup" |

### usart.h 头文件

```c
#ifndef __USART_H
#define __USART_H

#include "stm32f10x.h"

void USART1_Init(void);
void USART1_SendChar(uint8_t ch);
uint8_t USART1_ReceiveChar(void);

#endif
```

### usart.c 初始化函数

**完整初始化流程：**
```
① 开启时钟（GPIOA + USART1）
② 配置 GPIO 工作模式（PA9 复用推挽输出 + PA10 浮空输入）
③ 配置波特率（BRR = 0x271）
④ 配置数据帧格式（CR1/CR2 默认值）
⑤ 使能串口模块（CR1: UE + TE + RE）
```

**代码实现：**
```c
#include "usart.h"

void USART1_Init(void)
{
    /* ===== 第1步：开启时钟 ===== */
    RCC->APB2ENR |= RCC_APB2ENR_IOPAEN;    // GPIOA 时钟
    RCC->APB2ENR |= RCC_APB2ENR_USART1EN;  // USART1 时钟

    /* ===== 第2步：GPIO 工作模式 ===== */
    // PA9  - USART1_TX  → 复用推挽输出（MODE=11, CNF=10）
    // PA10 - USART1_RX  → 浮空输入     （MODE=00, CNF=01）

    // PA9：复用推挽输出，50MHz
    GPIOA->CRH &= ~(0xF << 4);   // 清空 bit[7:4]
    GPIOA->CRH |=  (0xB << 4);   // CNF=10, MODE=11 → 1011

    // PA10：浮空输入
    GPIOA->CRH &= ~(0xF << 8);   // 清空 bit[11:8]
    GPIOA->CRH |=  (0x4 << 8);   // CNF=01, MODE=00 → 0100

    /* ===== 第3步：波特率设置 ===== */
    USART1->BRR = 0x271;          // 115200 @ 72MHz

    /* ===== 第4步：数据帧格式（使用默认值） ===== */
    // CR1.M = 0   → 8 位数据位
    // CR1.PCE = 0 → 不使用校验
    // CR2.STOP = 00 → 1 位停止位
    // 以上均为复位默认值，可省略配置

    /* ===== 第5步：使能 ===== */
    USART1->CR1 |= USART_CR1_UE  |  // USART 使能
                   USART_CR1_TE  |  // 发送器使能
                   USART_CR1_RE;    // 接收器使能
}
```

### GPIO 配置速查

| 引脚 | 功能 | MODE[1:0] | CNF[1:0] | 4位组合 | 说明 |
|------|------|:---------:|:--------:|:-------:|------|
| PA9 | TX（发送/输出） | 11（50MHz） | 10（复用推挽） | **1011 = 0xB** | 复用推挽输出 |
| PA10 | RX（接收/输入） | 00（输入） | 01（浮空） | **0100 = 0x4** | 浮空输入 |

> PA9 和 PA10 都在 CRH（高寄存器）中配置，偏移量分别为 4（bit[7:4]）和 8（bit[11:8]）。

### 收发函数实现（轮询方式）

**发送一个字符：**
```c
void USART1_SendChar(uint8_t ch)
{
    // 等待 TXE = 1（发送数据寄存器为空）
    while (!(USART1->SR & USART_SR_TXE));

    // 写入数据到 DR
    USART1->DR = ch;
}
```

**接收一个字符：**
```c
uint8_t USART1_ReceiveChar(void)
{
    // 等待 RXNE = 1（接收数据寄存器非空）
    while (!(USART1->SR & USART_SR_RXNE));

    // 读取 DR 中的数据（硬件自动清除 RXNE）
    return (uint8_t)USART1->DR;
}
```

### 寄存器配置汇总

| 步骤 | 寄存器 | 配置位 | 值 | 作用 |
|:----:|--------|--------|:--:|------|
| 1 | RCC->APB2ENR | IOPAEN | 1 | 开启 GPIOA 时钟 |
| 1 | RCC->APB2ENR | USART1EN | 1 | 开启 USART1 时钟 |
| 2 | GPIOA->CRH | MODE9[1:0] + CNF9[1:0] | 1011 | PA9 复用推挽输出 |
| 2 | GPIOA->CRH | MODE10[1:0] + CNF10[1:0] | 0100 | PA10 浮空输入 |
| 3 | USART1->BRR | [15:0] | 0x271 | 115200 波特率 |
| 4 | USART1->CR1 | M | 0（默认） | 8 位数据 |
| 4 | USART1->CR1 | PCE | 0（默认） | 无校验 |
| 4 | USART1->CR2 | STOP[1:0] | 00（默认） | 1 位停止位 |
| 5 | USART1->CR1 | UE | 1 | USART 模块使能 |
| 5 | USART1->CR1 | TE | 1 | 发送器使能 |
| 5 | USART1->CR1 | RE | 1 | 接收器使能 |

### 硬件连接说明

```
┌─────────┐     USB      ┌──────────┐   调试线    ┌──────────────┐
│  电脑    │ ──────────→ │ ST-Link  │ ────────→  │   STM32      │
│ 串口助手  │             │ 2.1      │            │  PA9  = TX   │
│          │ ←────────── │ (USB转    │ ←──────── │  PA10 = RX   │
│          │             │  虚拟串口) │            │              │
└─────────┘              └──────────┘            └──────────────┘
```

## 注意事项 & 踩坑

- USART1 在 APB2 总线，时钟频率 72MHz，与 USART2~5 不同
- PA9 配复用推挽（非通用推挽），TX 是输出功能
- PA10 配浮空输入，RX 是输入功能
- BRR 值 0x271 对应 72MHz 下 115200 波特率，误差 0%
- 默认数据帧：8 位数据 + 无校验 + 1 位停止位，无需额外配置

## 相关笔记

- [[USART寄存器配置]]
- [[USART波特率配置]]
- [[USART1轮询方式收发]]

## 参考来源

- STM32F103参考手册
- 正点原子STM32开发板资料
