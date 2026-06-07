---
title: "USART1接收字符串实现"
category: "STM32/USART"
tags: [USART1, 接收字符串, IDLE, 空闲帧, 实现]
abstract: "USART1接收字符串的正确实现方法，解决双重while循环死锁问题，使用IDLE标志位判断接收结束"
source: "原创"
update_time: 2026-05-31
status: 完成
type: 实操
---

## 一句话定义

USART1接收字符串不能直接嵌套调用ReceiveChar，需要将IDLE检测移入内层循环，避免双重while循环导致死锁。

## 核心内容

### 初始思路（有缺陷）

**直接在外层判断 IDLE 的写法：**
```c
void USART1_ReceiveString(uint8_t *buffer, uint8_t *size)
{
    uint8_t i = 0;

    while (!(USART1->SR & USART_SR_IDLE))  // 外层：等待空闲帧
    {
        buffer[i] = USART1_ReceiveChar();  // 内层：接收一个字符（内部也有 while 循环）
        i++;
    }

    *size = i;
}
```

**缺陷分析：**
```
问题：双重 while 循环导致死锁

最后一个字符接收完毕
    ↓
IDLE 尚未置 1（需要一段时间才能检测到空闲帧）
    ↓
进入外层循环 → 调用 USART1_ReceiveChar()
    ↓
ReceiveChar 内部等待 RXNE = 1（永远不会来了）
    ↓
卡死在 ReceiveChar 的 while 循环中
    ↓
永远无法退出，无法回到外层判断 IDLE
```

> 核心矛盾：ReceiveChar 内部的 while 循环阻塞了对外层 IDLE 标志位的判断。

### 正确实现：将 IDLE 检测移入内层循环

**设计思路：**
- 不再调用底层 `ReceiveChar()` 函数，自行展开完整的接收逻辑
- 在**内层**等待 RXNE 的同时，**额外判断** IDLE 标志位
- 一旦检测到 IDLE 置 1，立即结束接收并返回

**代码实现：**
```c
void USART1_ReceiveString(uint8_t *buffer, uint8_t *size)
{
    uint8_t i = 0;

    while (1)   // 外层：持续接收字符
    {
        // 内层：等待当前字节接收完毕 或 检测到空闲帧
        while (!(USART1->SR & USART_SR_RXNE))
        {
            // 额外判断：是否检测到空闲帧
            if (USART1->SR & USART_SR_IDLE)
            {
                // 字符串接收完毕
                *size = i;
                return;
            }
        }

        // RXNE = 1，读取接收到的数据存入缓冲区
        buffer[i] = (uint8_t)USART1->DR;
        i++;
    }
}
```

**执行流程：**
```
外层 while(1) 循环：持续接收下一个字符
    │
    ├── 内层 while 循环：等待 RXNE = 1
    │       │
    │       ├── 每次循环额外判断 IDLE
    │       │       ├── IDLE = 1 → 字符串结束 → *size = i → return
    │       │       └── IDLE = 0 → 继续等待
    │       │
    │       └── RXNE = 1 → 退出内层循环
    │
    ├── buffer[i] = DR   → 保存字符
    ├── i++               → 计数+1
    │
    └── 继续外层循环，接收下一个字符
```

**关键设计要点：**

| 要点 | 说明 |
|------|------|
| 不调用 ReceiveChar | 避免其内部 while 循环阻塞 IDLE 检测 |
| IDLE 判断在内层 while 内部 | 每次等待 RXNE 时都检查 IDLE，确保不会漏检 |
| return 直接退出 | 检测到 IDLE 后赋值 size 并直接返回，无需 break |
| DR 读取自动清除 RXNE | 读取 DR 后硬件自动清除 RXNE 标志位 |

### 主函数测试

```c
#include "stm32f10x.h"
#include "usart.h"

// 全局变量：接收缓冲区和字符个数
uint8_t buffer[100];
uint8_t size = 0;

int main(void)
{
    USART1_Init();

    while (1)
    {
        // 接收字符串
        USART1_ReceiveString(buffer, &size);

        // 原封不动发回
        USART1_SendString(buffer, size);
    }
}
```

**测试结果：**

| 发送内容 | 收到内容 | 说明 |
|----------|----------|------|
| `Hello World` | `Hello World` | 正常回显 |
| `how are you` | `how are you` | 正常回显 |
| 多行连续发送 | 逐行完整回显 | 变长数据正确处理 |

### IDLE 标志位特性

| 特性 | 说明 |
|------|------|
| 置 1 条件 | RX 线路上检测到一个完整数据帧长度的**持续高电平**（空闲帧） |
| 清除方式 | **软件读 SR 后再读 DR** 可清除（先读后读） |
| 适用场景 | 变长数据接收（不知道对方发多少字节） |
| 置 1 时机 | 最后一个字节接收完毕后，经过一帧数据长度的空闲期 |

### 轮询方式收发字符串完整总结

| 函数 | 核心逻辑 | 结束条件 |
|------|----------|----------|
| **SendChar** | 等待 TXE=1 → 写 DR | 写入即完成 |
| **ReceiveChar** | 等待 RXNE=1 → 读 DR | 读取即完成 |
| **SendString** | for 循环逐个调用 SendChar | 遍历完指定个数 |
| **ReceiveString** | while(1) + 内层判断 RXNE 和 IDLE | 检测到 IDLE=1 |

## 注意事项 & 踩坑

- 不可嵌套调用 ReceiveChar：其内部 while 循环会阻塞外部 IDLE 检测
- buffer 长度需足够：全局数组定义时需预估最大接收长度（如 100）
- size 通过指针回传：函数无法预知接收长度，需用指针参数将个数传回调用方
- IDLE 清除方式：读 SR 再读 DR 可清除，本代码中读取 DR 时已隐含此操作
- 轮询方式局限：接收期间 CPU 持续空等，无法执行其他任务

## 相关笔记

- [[USART1字符串收发]]
- [[IDLE标志位处理与改进]]
- [[IDLE标志位清除机制]]

## 参考来源

- STM32F103开发板实验教程
