---
title: "USART1轮询方式收发"
category: "STM32/USART"
tags: [USART1, 轮询, TXE, RXNE, 收发]
abstract: "USART1轮询方式收发字符的实现，包括发送函数、接收函数和主函数测试"
source: "原创"
update_time: 2026-05-31
status: 完成
type: 实操
---

## 一句话定义

USART1轮询方式通过查询SR寄存器的TXE和RXNE标志位实现数据收发，发送等待TXE=1，接收等待RXNE=1。

## 核心内容

### 发送单个字符函数

**原理：**
- 查询 SR 寄存器的 **TXE** 标志位
- TXE = 0：发送缓冲区非空，继续等待
- TXE = 1：发送缓冲区为空，可写入新数据

**代码实现：**
```c
void USART1_SendChar(uint8_t ch)
{
    // 等待发送数据寄存器为空（TXE = 1）
    while (!(USART1->SR & USART_SR_TXE));

    // 写入数据到 DR，触发发送
    USART1->DR = ch;
}
```

**执行流程：**
```
while(SR.TXE == 0)  →  空等，硬件自动逐位发送
    ↓ TXE 变为 1
DR = ch             →  写入新数据，硬件开始下一次发送
```

### 接收单个字符函数

**原理：**
- 查询 SR 寄存器的 **RXNE** 标志位
- RXNE = 0：接收缓冲区为空（未收到数据），继续等待
- RXNE = 1：接收缓冲区非空（已收到数据），可读取

**代码实现：**
```c
uint8_t USART1_ReceiveChar(void)
{
    // 等待接收数据寄存器非空（RXNE = 1）
    while (!(USART1->SR & USART_SR_RXNE));

    // 读取 DR 中的数据，读取后硬件自动清除 RXNE
    return (uint8_t)USART1->DR;
}
```

**执行流程：**
```
while(SR.RXNE == 0)  →  空等，等待外部数据到达
    ↓ RXNE 变为 1
return DR            →  读取数据，硬件清除 RXNE，可接收下一个
```

### 主函数测试

**测试一：发送字符到电脑**
```c
#include "stm32f10x.h"
#include "usart.h"
#include "delay.h"

int main(void)
{
    USART1_Init();

    USART1_SendChar('A');     // 发送单个字符
    USART1_SendChar('T');
    USART1_SendChar('\n');    // 换行

    while (1)
    {
        USART1_SendChar('X');
        USART1_SendChar('\n');
        Delay_ms(1000);       // 每隔 1 秒发送一次
    }
}
```

**预期结果：** 串口助手每秒收到一个 "X" 加换行。

**测试二：接收并回显（Echo）**
```c
int main(void)
{
    USART1_Init();

    USART1_SendChar('A');
    USART1_SendChar('T');
    USART1_SendChar('\n');

    while (1)
    {
        uint8_t ch = USART1_ReceiveChar();   // 接收一个字符
        USART1_SendChar(ch);                  // 原封不动发回
    }
}
```

**预期结果：** 电脑发送任意字符，STM32 立即回传相同字符。

**测试三：小写转大写回显**
```c
int main(void)
{
    USART1_Init();

    USART1_SendChar('A');
    USART1_SendChar('T');
    USART1_SendChar('\n');

    while (1)
    {
        uint8_t ch = USART1_ReceiveChar();
        USART1_SendChar(ch - 32);   // 小写 ASCII - 32 = 大写 ASCII
    }
}
```

**预期结果：** 发送 "a" 收到 "A"，发送 "h" 收到 "H"。

### ASCII 码参考

| 字符 | ASCII 码 | 说明 |
|------|:--------:|------|
| 'A' | 65 | 大写字母起始 |
| 'Z' | 90 | 大写字母结束 |
| 'a' | 97 | 小写字母起始 |
| 'z' | 122 | 小写字母结束 |
| 大小写差值 | **32** | 小写 - 32 = 大写 |

> 前提：转换仅对小写字母有效（ASCII 97~122），对非字母字符不适用。

### 串口调试工具使用

| 操作 | 说明 |
|------|------|
| 打开工具 | 使用资料中的串口调试助手 |
| 选择端口 | 设备管理器中查看 ST-Link 虚拟串口的 COM 号 |
| 波特率设置 | 与代码一致（115200） |
| 勾选项 | 建议勾选"加时间戳"和"分包显示"，便于观察收发 |
| 发送数据 | 在发送框输入内容，点击发送 |
| 接收数据 | 接收区自动显示 STM32 返回的数据 |

### 关键寄存器操作回顾

| 操作 | 寄存器 | 位 | 含义 |
|------|--------|-----|------|
| 等待发送 | SR | TXE | 发送缓冲区为空 → 可写入 |
| 等待接收 | SR | RXNE | 接收缓冲区非空 → 可读取 |
| 写入发送数据 | DR | [8:0] | 写入后硬件自动发送 |
| 读取接收数据 | DR | [8:0] | 读取后硬件自动清除 RXNE |

## 注意事项 & 踩坑

- 复位后重新连接：烧写完成后需关闭再打开串口，或按复位键重新开始
- TXE vs TC：本实验使用 TXE（更快），不要求等待移位寄存器彻底发完
- RXNE 自动清除：读取 DR 时硬件自动清除 RXNE，无需手动操作
- TXE 不自动清除：写入 DR 后硬件自动清除 TXE
- 轮询方式的局限：while 循环等待期间 CPU 无法执行其他任务

## 相关笔记

- [[USART1初始化代码实现]]
- [[USART寄存器配置]]
- [[USART1字符串收发]]

## 参考来源

- STM32F103开发板实验教程
