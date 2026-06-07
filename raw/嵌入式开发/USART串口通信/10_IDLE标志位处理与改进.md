---
title: "IDLE标志位处理与改进"
category: "STM32/USART"
tags: [IDLE, 空闲帧, 清除机制, 改进方案, ReceiveChar]
abstract: "IDLE标志位的处理方法和两种改进方案，解决IDLE未清除导致的循环输出bug"
source: "原创"
update_time: 2026-05-31
status: 完成
type: 踩坑
---

## 一句话定义

IDLE标志位不会自动清零，必须通过软件序列（先读SR再读DR）手动清除，否则会导致循环输出bug。

## 核心内容

### 回顾：轮询方式核心状态位

**接收状态位 — RXNE：**

| 项目 | 说明 |
|------|------|
| 名称 | RXNE（Receive data Register Not Empty） |
| 含义 | 接收数据寄存器**非空**（已收到一个完整字节） |
| 置 1 | 硬件自动：接收移位寄存器将数据并行传入 RDR 后 |
| 清零 | **读取 DR 时硬件自动清零**（对 DR 做读操作即可） |
| 轮询逻辑 | while(RXNE == 0) 等待 → RXNE == 1 后读取 DR |

**发送状态位 — TXE：**

| 项目 | 说明 |
|------|------|
| 名称 | TXE（Transmit data register Empty） |
| 含义 | 发送数据寄存器**为空**（数据已移入移位寄存器） |
| 置 1 | 硬件自动：TDR 数据交给发送移位寄存器后 |
| 清零 | **写入 DR 时硬件自动清零**（对 DR 做写操作即可） |
| 轮询逻辑 | while(TXE == 0) 等待 → TXE == 1 后写入 DR |

**空闲帧标志位 — IDLE：**

| 项目 | 说明 |
|------|------|
| 名称 | IDLE（Idle Line Detected） |
| 含义 | 检测到 RX 线路持续一个完整数据帧长度的**高电平**（空闲帧） |
| 置 1 | 硬件自动：接收完最后一个字节后，线路持续空闲 |
| 清零 | **软件序列：先读 SR，再读 DR**（硬件自动清零） |
| 用途 | 判断变长数据（如字符串）接收完毕 |

> IDLE 清零方式与 RXNE/TXE 不同，不能通过单次读/写 DR 清除，必须执行"读 SR → 读 DR"的软件序列。

### 改进方案一：重写内层循环（双重 while）

**设计思路：** 不调用 `ReceiveChar()`，自行展开接收逻辑，在内层等待 RXNE 的同时额外判断 IDLE：

```c
void USART1_ReceiveString(uint8_t *buffer, uint8_t *size)
{
    uint8_t i = 0;

    while (1)   // 外层：持续接收下一个字符
    {
        // 内层：等待当前字节接收完毕 或 检测到空闲帧
        while (!(USART1->SR & USART_SR_RXNE))
        {
            if (USART1->SR & USART_SR_IDLE)
            {
                *size = i;
                return;     // 检测到空闲帧，直接返回
            }
        }

        buffer[i] = (uint8_t)USART1->DR;  // 读取数据
        i++;
    }
}
```

### 改进方案二：修改 ReceiveChar 增加 IDLE 判断

**设计思路：** 在原有 `ReceiveChar()` 的 while 循环中增加 IDLE 判断作为退出机制：

```c
uint8_t USART1_ReceiveChar(void)
{
    while (!(USART1->SR & USART_SR_RXNE))
    {
        // 新增：检测到空闲帧则提前退出
        if (USART1->SR & USART_SR_IDLE)
        {
            return 0;   // 返回 0 作为退出标志
        }
    }

    return (uint8_t)USART1->DR;
}
```

配合 `ReceiveString` 使用原有逻辑：
```c
void USART1_ReceiveString(uint8_t *buffer, uint8_t *size)
{
    uint8_t i = 0;

    while (!(USART1->SR & USART_SR_IDLE))
    {
        buffer[i] = USART1_ReceiveChar();
        i++;
    }

    *size = i - 1;  // 减去 IDLE 退出时多计的一次

    // ===== 关键：清除 IDLE 标志位 =====
    USART1->DR;      // 读取 DR 完成"读SR → 读DR"软件序列
}
```

### 问题：IDLE 标志位未清除

直接使用上述代码会出现**循环输出**的问题：

```
第一轮：接收字符串 → 发送回显 → 正常
第二轮：再次调用 ReceiveString → IDLE 仍为 1 → 跳过 while 循环 → 再次输出
        ...（无限循环，持续输出上一次的内容）
```

原因：IDLE 标志位**不会自动清零**，必须通过软件序列手动清除。

### IDLE 标志位清除机制

**清除方法：**

| 操作 | 说明 |
|------|------|
| **软件序列** | 先读 SR，再读 DR（硬件自动清零 IDLE） |
| 代码实现 | `USART1->SR;`（读 SR）+ `USART1->DR;`（读 DR） |

**清除原理：**
```
读 SR → 确认已检测到空闲状态
读 DR → 确认已将所有接收到的数据取走
    → 硬件判定：空闲状态已被处理，清除 IDLE 标志
```

**完整清除代码：**
```c
// 接收字符串结束后，清除 IDLE 标志位
volatile uint32_t temp;
temp = USART1->SR;    // 读 SR（第一步）
temp = USART1->DR;    // 读 DR（第二步）
(void)temp;           // 避免编译器优化掉未使用的读操作
```

> 使用 `volatile` 或 `(void)` 防止编译器将"无用"的读操作优化掉，确保两次读取真正执行。

### 完整的 ReceiveString 实现

**ReceiveChar（含 IDLE 退出机制）：**
```c
uint8_t USART1_ReceiveChar(void)
{
    while (!(USART1->SR & USART_SR_RXNE))
    {
        if (USART1->SR & USART_SR_IDLE)
        {
            return 0;
        }
    }
    return (uint8_t)USART1->DR;
}
```

**ReceiveString：**
```c
void USART1_ReceiveString(uint8_t *buffer, uint8_t *size)
{
    uint8_t i = 0;

    while (!(USART1->SR & USART_SR_IDLE))
    {
        buffer[i] = USART1_ReceiveChar();
        i++;
    }

    *size = i - 1;

    // 清除 IDLE 标志位（读 SR + 读 DR 软件序列）
    volatile uint32_t temp;
    temp = USART1->SR;
    temp = USART1->DR;
    (void)temp;
}
```

### 三种状态位清零方式对比

| 状态位 | 置 1 条件 | 清零方式 | 涉及操作 |
|--------|-----------|----------|----------|
| **RXNE** | 接收到一个完整字节（RDR 非空） | 读 DR **自动清零** | 单次读 DR |
| **TXE** | TDR 数据移入移位寄存器（TDR 为空） | 写 DR **自动清零** | 单次写 DR |
| **IDLE** | RX 线路持续空闲一个数据帧长度 | **软件序列**：先读 SR 再读 DR | 读 SR + 读 DR |

## 注意事项 & 踩坑

- IDLE 必须手动清零：不像 RXNE/TXE 可通过单次读/写自动清除，需要软件序列
- 防止编译器优化：读 SR 和 DR 的结果未使用，需用 `volatile` 或 `(void)` 防止被优化
- ReceiveChar 返回 0 的含义：IDLE 退出时返回 0，恰好可作为字符串结束符 `\0`，但需注意是否影响 size 计算
- `*size = i - 1`：最后一次 ReceiveChar 因 IDLE 退出而多计一次，需减 1
- 调试器必须连接：串口通讯依赖 ST-Link 的虚拟串口功能，仅接 USB 供电无法收发

## 相关笔记

- [[USART1接收字符串实现]]
- [[IDLE标志位清除机制]]
- [[状态寄存器状态变化]]

## 参考来源

- STM32F103开发板实验教程
- USART寄存器手册
