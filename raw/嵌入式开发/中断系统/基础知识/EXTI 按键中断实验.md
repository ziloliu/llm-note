---
title: "EXTI 按键中断实验"
category: "STM32/中断系统"
tags: [EXTI, 按键中断, 实验案例, 寄存器配置, 代码实现]
abstract: "EXTI 按键中断实验：通过外部中断实现按键控制 LED 灯，包含硬件分析、寄存器配置和代码实现。"
source: "原创"
update_time: 2026-05-28
status: 完成
type: 实操
---

## 一句话定义

EXTI 按键中断实验通过配置 GPIO、AFIO、EXTI 和 NVIC，实现按键触发外部中断控制 LED 灯的亮灭，包含完整的硬件分析、寄存器配置和代码实现。

## 核心内容

### 实验需求

| 项目 | 内容 |
|------|------|
| 功能 | 按下按键 K3，翻转 LED1 的亮灭状态（亮→灭，灭→亮） |
| 实现方式 | 外部中断（非轮询） |
| 选择中断的理由 | 按键按下时机不确定，中断比轮询更高效 |

### 硬件电路分析

#### LED1 电路

| 项目 | 内容 |
|------|------|
| 连接引脚 | **PA0** |
| 工作模式 | 通用推挽输出 |
| 驱动方式 | PA0 输出**低电平**点亮，**高电平**熄灭 |
| 实现翻转 | 调用 `GPIO_WriteBit()` 或读取当前输出状态取反 |

#### K3 按键电路

| 项目 | 内容 |
|------|------|
| 连接引脚 | **PF10** |
| 工作模式 | 通用输入（上下拉输入） |
| 硬件连接 | 按键一端接 PF10，另一端接 **3.3V** |
| 按下电平 | **高电平**（3.3V 直接接入） |
| 默认电平 | 需通过下拉电阻保持为**低电平** |
| 输入模式配置 | CNF 配置为 10（上下拉输入），ODR 写 0 选择**下拉** |

#### 引脚电平变化

```
未按下：PF10 = 低电平（下拉）
按下后：PF10 = 高电平（3.3V 接入）
→ 检测上升沿触发外部中断
```

### 时钟使能

需要开启以下外设时钟：

| 时钟 | 原因 |
|------|------|
| **GPIOA** 时钟 | LED1 所在端口，PA0 输出控制 |
| **GPIOF** 时钟 | K3 所在端口，PF10 输入检测 |
| **AFIO** 时钟 | 外部中断使用 AFIO 复用功能（7 合 1 归并） |

> 注意：EXTI 无需单独开启时钟，AFIO 时钟开启后 EXTI 即可使用。

### EXTI 配置要点

#### GPIO 配置

| 配置项 | PA0（LED1） | PF10（K3） |
|--------|------------|------------|
| 模式 | 推挽输出 | 上下拉输入 |
| 上拉/下拉 | — | **下拉**（ODR 写 0） |

#### AFIO 复用配置

- 将 PF10 映射到 EXTI10 通道
- 即选择 GPIOF 的第 10 号引脚作为 EXTI10 的中断源

#### EXTI 寄存器配置

| 配置项 | 操作 | 说明 |
|--------|------|------|
| 触发方式 | **上升沿触发选择寄存器（RTSR）** 第 10 位置 1 | 按键按下产生上升沿 |
| 中断屏蔽 | **中断屏蔽寄存器（IMR）** 第 10 位置 1 | 打开 EXTI10 中断通路 |

#### NVIC 配置

| 配置项 | 操作 |
|--------|------|
| 中断通道 | EXTI15_10_IRQn（EXTI10 属于 EXTI15~10 共享通道） |
| 优先级 | 根据需求配置抢占优先级和响应优先级 |
| 使能 | 开启该中断通道 |

### 软件防抖处理

#### 问题

按键无硬件防抖电路，按下瞬间可能产生机械抖动，导致：
- 多次误触发中断
- 翻转状态异常（亮→灭→亮 或 灭→亮→灭）

#### 解决方案

在中断服务程序中加入**软件延时防抖**：

```c
// 中断服务程序伪代码
void EXTI15_10_IRQHandler(void)
{
    // 1. 延时 10~15ms（消除机械抖动）
    Delay_ms(15);

    // 2. 再次确认 PF10 是否仍为高电平（真的按下了）
    if (GPIO_ReadInputDataBit(GPIOF, GPIO_Pin_10) == Bit_SET)
    {
        // 3. 翻转 LED1 状态
        // 读取 PA0 当前输出状态并取反
    }

    // 4. 清除 EXTI10 挂起位（PR 第 10 位写 1 清零）
}
```

#### 防抖原理

```
按键按下 → 检测到上升沿 → 进入中断 → 延时15ms → 再次读取引脚电平
    ├── 仍为高电平 → 确认按下 → 执行翻转 → 清除挂起位
    └── 变为低电平 → 抖动误触发 → 不执行操作 → 清除挂起位
```

### 完整初始化流程

```
① 开启时钟
   - GPIOA（LED1）
   - GPIOF（K3）
   - AFIO

② GPIO 初始化
   - PA0：推挽输出（控制 LED1）
   - PF10：下拉输入（检测按键）

③ AFIO 配置
   - 将 PF10 映射到 EXTI10

④ EXTI 配置
   - 上升沿触发（RTSR 第 10 位置 1）
   - 中断使能（IMR 第 10 位置 1）

⑤ NVIC 配置
   - 使能 EXTI15_10 中断通道
   - 设置优先级

⑥ 编写中断服务程序
   - EXTI15_10_IRQHandler()
   - 软件防抖 → 确认按键 → 翻转 LED1 → 清除挂起位
```

### 寄存器配置详解

#### AFIO EXTICR 配置

```
EXTICR[2] 对应 EXTICR3，管理 EXTI8~EXTI11
EXTI10 占 bit[11:8]，填入 0101（GPIOF 编码）

位分布：
  bit[15:12] = 保留
  bit[11:8]  = EXTI10 → 0101 (PF)
  bit[7:4]   = EXTI9  → 0000 (PA，默认)
  bit[3:0]   = EXTI8  → 0000 (PA，默认)

0x0005 实际写入值等效于 bit[11:8] = 0101 的效果
（注：0x0500 更精确，0x0005 会同时影响 EXTI8 字段，但 EXTI8 未使用不影响）
```

#### AFIO EXTICR 寄存器与 EXTI 线对应

| 寄存器 | EXTICR[x] | 管理 EXTI 线 | 每线 4 位 |
|--------|-----------|-------------|----------|
| EXTICR1 | [0] | EXTI0 ~ EXTI3 | bit[3:0] ~ bit[15:12] |
| EXTICR2 | [1] | EXTI4 ~ EXTI7 | bit[3:0] ~ bit[15:12] |
| EXTICR3 | [2] | EXTI8 ~ EXTI11 | bit[3:0] ~ bit[15:12] |
| EXTICR4 | [3] | EXTI12 ~ EXTI15 | bit[3:0] ~ bit[15:12] |

### 代码实现

#### key.h 头文件

```c
#ifndef __KEY_H
#define __KEY_H

#include "stm32f10x.h"

void Key_Init(void);

#endif
```

#### key.c 初始化函数

```c
#include "key.h"

void Key_Init(void)
{
    /* ===== 第1步：开启时钟 ===== */
    RCC->APB2ENR |= RCC_APB2ENR_IOPFEN;   // GPIOF 时钟
    RCC->APB2ENR |= RCC_APB2ENR_AFIOEN;    // AFIO 时钟

    /* ===== 第2步：GPIO 工作模式（PF10 下拉输入） ===== */
    GPIOF->CRH &= ~(0xF << 8);   // 清空 bit11:8（MODE10[1:0] 和 CNF10[1:0]）
    GPIOF->CRH |=  (0x8 << 8);   // CNF=10(上下拉输入), MODE=00(输入)

    // 补充 A 代码：将 MODE10[1:0] 确保为 00（上一步已实现，此处可省略）
    // GPIOF->CRH &= ~GPIO_CRH_MODE10;

    // 补充 B 代码：将 CNF10[1:0] 设为 10
    GPIOF->CRH |=  GPIO_CRH_CNF10_1;    // CNF10[1] = 1
    GPIOF->CRH &= ~GPIO_CRH_CNF10_0;    // CNF10[0] = 0

    GPIOF->ODR &= ~GPIO_ODR_ODR10;       // ODR10 = 0，选择下拉

    /* ===== 第3步：AFIO 引脚复用选择（七合一） ===== */
    // PF10 → EXTI10，EXTICR3 管理 EXTI8~11，对应数组下标 [2]
    // GPIOF 编码 = 0101，放在 EXTI10 的 4 位字段中
    // EXTICR3 bit[11:8] 对应 EXTI10，填入 0101 → 0x0005 << 8
    AFIO->EXTICR[2] |= 0x0005;   // 实际影响 bit[11:8] = 0101 = GPIOF

    /* ===== 第4步：EXTI 配置 ===== */
    EXTI->RTSR |= EXTI_RTSR_TR10;   // 上升沿触发（bit10 置 1）
    EXTI->IMR  |= EXTI_IMR_MR10;    // 开放中断屏蔽（bit10 置 1）

    /* ===== 第5步：NVIC 配置（调用库函数） ===== */
    // 设置优先级分组：模式3（全抢占优先级）
    NVIC_SetPriorityGrouping(NVIC_PriorityGroup_3);

    // 设置 EXTI15_10 的抢占优先级为 3
    NVIC_SetPriority(EXTI15_10_IRQn, 3);

    // 使能 EXTI15_10 中断通道
    NVIC_EnableIRQ(EXTI15_10_IRQn);
}
```

#### 中断服务程序

```c
#include "key.h"
#include "led.h"
#include "delay.h"

void EXTI15_10_IRQHandler(void)
{
    // 第1步：清除挂起标志位（写1清零，必须尽早执行）
    EXTI->PR = EXTI_PR_PR10;

    // 第2步：软件防抖延时
    Delay_ms(10);

    // 第3步：再次确认 PF10 仍为高电平（真正按下）
    if (GPIOF->IDR & GPIO_IDR_IDR10)   // 不等于0即可，不能判断等于1
    {
        // 第4步：翻转 LED1 状态
        LED1_Turn();
    }
}
```

#### 电平判断注意事项

```c
// ❌ 错误写法
if ((GPIOF->IDR & GPIO_IDR_IDR10) == 1)  // IDR10 在 bit10，与操作后值为 0x0400，永远不等于 1

// ✅ 正确写法
if (GPIOF->IDR & GPIO_IDR_IDR10)          // 非零即为真，bit10 为高时值为 0x0400 ≠ 0
if ((GPIOF->IDR & GPIO_IDR_IDR10) != 0)   // 同上，等价写法
if ((GPIOF->IDR & GPIO_IDR_IDR10) == GPIO_IDR_IDR10)  // 精确匹配，也可以
```

#### main.c 主函数

```c
#include "stm32f10x.h"
#include "led.h"
#include "key.h"

int main(void)
{
    LED_Init();    // 初始化 LED（PA0 推挽输出）
    Key_Init();    // 初始化按键（PF10 下拉输入 + EXTI + NVIC）

    while (1)
    {
        // 主循环无需任何操作
        // 按键检测和 LED 翻转全部在中断服务程序中完成
    }
}
```

### 配置流程与信号流对应

```
信号流方向                    代码配置步骤
                    
GPIOF PIN10 (下拉输入)   →   ① 开启 GPIOF 时钟 + 配置 CRH/ODR
         ↓
AFIO 七合一复用选择       →   ② 配置 AFIO->EXTICR[2] = 0x0005
         ↓
EXTI 边缘检测 + 屏蔽     →   ③ 配置 EXTI->RTSR | EXTI->IMR
         ↓
NVIC 优先级 + 使能       →   ④ 调用 NVIC 库函数（SetPriorityGrouping / SetPriority / EnableIRQ）
         ↓
内核响应执行              →   ⑤ 编写 EXTI15_10_IRQHandler 中断服务程序
```

### 实验验证结果

| 操作 | 预期效果 | 实际效果 |
|------|----------|----------|
| 按下 K3（首次） | LED1（黄灯）点亮 | LED1 点亮 |
| 再次按下 K3 | LED1 熄灭 | LED1 熄灭 |
| 重复按键 | 反复翻转亮灭 | 正常翻转 |
| 防抖效果 | 无明显闪烁或毛刺 | 防抖有效，状态切换稳定 |

### 关键寄存器速查表

| 寄存器             | 所属模块 | 功能               | 本实验操作            |
| --------------- | ---- | ---------------- | ---------------- |
| MODER / CRL+CRH | GPIO | 端口模式配置           | 00（输入）           |
| CNF             | GPIO | 输入/输出类型          | 10（上下拉输入）        |
| ODR             | GPIO | 输出数据 / 输入时选择上下拉  | 0（下拉）            |
| IDR             | GPIO | 输入数据寄存器          | 读取判断电平           |
| EXTICR[0~3]     | AFIO | EXTI 线的 GPIO 组选择 | [2] = 0x0005（PF） |
| RTSR            | EXTI | 上升沿触发选择          | bit10 = 1        |
| IMR             | EXTI | 中断屏蔽控制           | bit10 = 1（开放）    |
| PR              | EXTI | 请求挂起标志           | 中断后写 1 清零 bit10  |

## 注意事项 & 踩坑

- **AFIO 时钟必须开启**: 外部中断依赖 AFIO 复用功能，不开启则 EXTI 无法收到信号
- **ODR 写 0 实现下拉**: 输入模式下 CNF=10 为上下拉输入，通过 ODR 选择上拉（1）或下拉（0）
- **必须清除挂起位**: 中断服务程序末尾需将 PR 对应位写 1 清零，否则中断持续触发
- **EXTI15_10 共享通道**: EXTI10 和 EXTI11~15 共用同一个中断入口函数，需在服务程序中判断具体是哪个 EXTI 线触发
- **电平判断**: 不能使用 `== 1` 判断高位引脚，应使用 `!= 0` 或直接作为布尔值判断
- **大容量芯片宏定义**: F103 大容量芯片才有 GPIOF/GPIOG，需在 `stm32f10x.h` 中启用 `STM32F10X_HD` 宏

## 相关笔记

- [[EXTI 按键中断实验 HAL 库方式]]
- [[STM32 中断体系架构]]
- [[外部中断控制器 EXTI]]
- [[NVIC 嵌套向量中断控制器]]
- [[NVIC 中断优先级配置机制]]
- [[中断优先级配置]]

## 参考来源

- STM32F103 参考手册 RM0008
- 原始笔记：EXTI 按键中断控制 LED 灯实验案例.md、EXTI 按键中断实验寄存器配置详解.md、EXTI 按键中断实验代码实现.md