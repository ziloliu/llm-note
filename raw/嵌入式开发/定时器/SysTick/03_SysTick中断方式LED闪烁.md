# SysTick 系统滴答定时器 — 中断方式实现 LED 闪烁 笔记

---

## 一、实验需求

| 需求 | 说明 |
|------|------|
| 功能 | LED1（黄灯）每隔 1 秒闪烁一次 |
| 实现方式 | SysTick **中断方式**（非轮询） |
| 引脚 | PA0，低电平点亮，高电平熄灭 |

---

## 二、轮询方式 vs 中断方式

| 对比项 | 轮询方式（之前） | 中断方式（本次） |
|--------|-----------------|-----------------|
| 实现方式 | `while(!COUNTFLAG)` 等待 | 中断服务函数自动执行 |
| CPU 占用 | 高（一直循环等待） | **低**（只在中断时执行） |
| 响应性 | 阻塞主程序 | **不阻塞**主程序 |
| 被其他中断打断 | 可能卡死/延时 | 正常工作 |
| 适用场景 | 简单延时 | **推荐**方式 |

---

## 三、24 位计数器容量限制

### 3.1 问题分析

```
目标：1 秒定时
每次滴答 = 1/72 μs
所需装载值 = 72,000,000

24 位最大值 = 2^24 - 1 = 16,777,215 ≈ 16.7M

72,000,000 > 16,777,215  →  超出 24 位范围！
```

### 3.2 解决方案：分段计数

```
将 1 秒分解为：
  → 每 1ms 产生一次中断（LOAD = 71999）
  → 在中断中累加计数器 counter
  → 累加到 1000 次 = 1 秒
  → 执行 LED 翻转

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  中断 #1     │     │  中断 #2     │     │  中断 #1000  │
│  1ms         │     │  2ms         │     │  1000ms=1s   │
│  counter=1   │ ──→ │  counter=2   │ ──→ │  counter=1000│
│              │     │              │     │  翻转 LED!   │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

## 四、LOAD 值计算与减 1 说明

### 4.1 计算过程

```
目标：每次中断间隔 = 1ms = 1000μs
每次滴答 = 1/72 μs
所需滴答次数 = 1000μs / (1/72)μs = 72000 次

LOAD = 72000 - 1 = 71999（⚠️ 必须减 1）
```

### 4.2 为什么需要减 1

```
计数器工作过程（LOAD = 72000 时）：
  72000 → 71999 → ... → 1 → 0 → 产生中断
  共计数 72001 次 ❌

计数器工作过程（LOAD = 71999 时）：
  71999 → 71998 → ... → 1 → 0 → 产生中断
  共计数 72000 次 ✅

原因：从 N 减到 0，共经过 N+1 个值
     （类似 C 语言数组下标 0~N-1 共 N 个元素）
```

---

## 五、CTRL 寄存器配置详解

### 5.1 配置步骤（逐步置位）

| 步骤 | 操作 | 寄存器位 | 含义 |
|:----:|------|----------|------|
| ① | `CTRL \|= CLKSOURCE` | bit2 = 1 | 选择 AHB 时钟（72MHz） |
| ② | `CTRL \|= TICKINT` | bit1 = 1 | 使能中断 |
| ③ | `CTRL \|= ENABLE` | bit0 = 1 | 使能定时器 |

### 5.2 配置顺序说明

```
① 先配置 LOAD（重装载值）
② 配置时钟源（CLKSOURCE）
③ 开启中断（TICKINT）
④ 最后开启定时器（ENABLE）

⚠️ ENABLE 必须最后设置，确保所有参数已就绪
```

---

## 六、NVIC 配置说明

```
问题：开启了 TICKINT 中断，为什么不需要配置 NVIC？

答案：SysTick 是 Cortex-M3 内核异常，不是外设中断
  → 在内核启动代码（startup_stm32f103xx.s）中已自动配置
  → 在系统库文件（core_cm3.c）中已处理 NVIC 使能
  → 无需用户手动配置 NVIC
```

---

## 七、工程结构

```
Project/
├── Hardware/
│   └── LED/              ← LED 驱动（已有）
│       ├── led.c
│       └── led.h
├── User/
│   ├── main.c            ← 主函数
│   ├── systick.c         ← SysTick 初始化 + 中断服务函数
│   └── systick.h         ← 头文件
└── Core/Src/
```

> SysTick 属于内核定时器，直接放在 User 目录下，无需新建 Hardware 子目录。

---

## 八、代码实现

### 8.1 systick.h

```c
#ifndef __SYSTICK_H
#define __SYSTICK_H

#include "stm32f10x.h"

void SysTick_Init(void);

#endif
```

### 8.2 systick.c

```c
#include "systick.h"
#include "led.h"

/* 全局变量：毫秒计数器 */
uint16_t counter = 0;

/**
 * @brief  SysTick 初始化：每 1ms 产生一次中断
 */
void SysTick_Init(void)
{
    /* ① 设置重装载值：1ms = 72000 次滴答 */
    SysTick->LOAD = 72000 - 1;     // 71999

    /* ② 选择时钟源：AHB 处理器时钟 72MHz */
    SysTick->CTRL |= SysTick_CTRL_CLKSOURCE_Msk;

    /* ③ 使能中断 */
    SysTick->CTRL |= SysTick_CTRL_TICKINT_Msk;

    /* ④ 使能定时器（最后开启） */
    SysTick->CTRL |= SysTick_CTRL_ENABLE_Msk;
}

/**
 * @brief  SysTick 中断服务函数
 * @note   每 1ms 进入一次
 */
void SysTick_Handler(void)
{
    counter++;

    if (counter == 1000)     // 1000ms = 1s
    {
        LED1_Toggle();       // 翻转 LED1
        counter = 0;         // 清零重新计数
    }
}
```

### 8.3 main.c

```c
#include "stm32f10x.h"
#include "led.h"
#include "systick.h"

int main(void)
{
    LED_Init();          // 初始化 LED
    SysTick_Init();      // 初始化 SysTick（每 1ms 中断）

    // 主函数无需任何操作，中断服务函数自动执行 LED 翻转
    while (1)
    {
        // 空循环，等待中断
    }
}
```

---

## 九、执行流程

```
系统上电
    │
    ├── LED_Init()       → 配置 PA0 为推挽输出
    │
    ├── SysTick_Init()   → 配置 SysTick
    │   ├── LOAD = 71999        （1ms 装载值）
    │   ├── CLKSOURCE = 1       （72MHz）
    │   ├── TICKINT = 1         （使能中断）
    │   └── ENABLE = 1          （启动计数）
    │
    ├── main while(1)    → 主循环空转
    │
    └── 每 1ms 触发 SysTick_Handler()
        ├── counter++
        ├── counter == 1000 ?
        │   ├── YES → LED1_Toggle() + counter = 0
        │   └── NO  → 返回，继续等待
        └── 返回主循环
```

---

## 十、中断服务函数名称查找

```c
// 在启动文件 startup_stm32f103xx.s 中的中断向量表查找

DCD     SysTick_Handler          ; SysTick

// 对应 Cortex-M3 内核异常向量表的第 15 项（最后一个内部异常）
// 名称：SysTick_Handler
```

---

## 十一、主函数中的两种处理方式

### 方式一：中断中直接操作（本实验）

```c
void SysTick_Handler(void)
{
    counter++;
    if (counter == 1000)
    {
        LED1_Toggle();    // 直接在中断中翻转
        counter = 0;
    }
}

// main 中 while(1) 空循环
```

### 方式二：中断中设置标志，主循环中操作

```c
volatile uint8_t flag = 0;

void SysTick_Handler(void)
{
    counter++;
    if (counter == 1000)
    {
        flag = 1;         // 仅设置标志
        counter = 0;
    }
}

// main 中
while (1)
{
    if (flag)
    {
        LED1_Toggle();
        flag = 0;
    }
}
```

> 两种方式均可，方式二更灵活（主循环中可做其他事情）。

---

## 十二、counter 变量数据类型选择

| 类型 | 范围 | 是否满足 |
|------|------|:--------:|
| `uint8_t` | 0 ~ 255 | ❌（不够 1000） |
| `uint16_t` | 0 ~ 65535 | ✅（推荐） |
| `uint32_t` | 0 ~ 4294967295 | ✅（范围更大） |

> 需要计到 1000，至少使用 `uint16_t`。

---

## 十三、寄存器配置总结

| 步骤 | 寄存器 | 操作 | 值 | 含义 |
|:----:|--------|------|:--:|------|
| ① | LOAD | 写入 | **71999** | 1ms 重装载值 |
| ② | CTRL.CLKSOURCE | 置 1 | 1 | 72MHz 时钟源 |
| ③ | CTRL.TICKINT | 置 1 | 1 | 使能中断 |
| ④ | CTRL.ENABLE | 置 1 | 1 | 启动定时器 |

---

## 十四、SysTick 使用方式对比总结

| 对比项 | 轮询方式 | 中断方式 |
|--------|----------|----------|
| CTRL 配置 | `0x05`（101） | `0x07`（111） |
| TICKINT | 0（不开中断） | 1（开中断） |
| 等待方式 | `while(!(CTRL & COUNTFLAG))` | 中断服务函数自动执行 |
| CPU 占用 | 高 | 低 |
| 是否阻塞 | 阻塞 | 不阻塞 |
| 是否需要中断服务函数 | 不需要 | 需要 `SysTick_Handler()` |
| 是否需要 NVIC 配置 | 不需要 | 不需要（内核自动处理） |
| 适用场景 | 简单延时 | 定时任务、操作系统时基 |