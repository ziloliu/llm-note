# DMA 内存到串口传输 — 寄存器方式实现 笔记

---

## 一、实验概述

| 项目 | 说明 |
|------|------|
| 传输方向 | **RAM（存储器）→ USART1_DR/TDR（外设）** |
| DMA 控制器 | DMA1 |
| 通道 | **通道 4**（硬件固定，USART1_TX） |
| 数据宽度 | 8 位（字节） |
| 传输数据 | "abcd"（4 个字节） |

---

## 二、与存储器到存储器模式的关键区别

| 对比项 | 存储器到存储器 | 内存到串口 |
|--------|:-------------:|:---------:|
| MEM2MEM | **1**（开启） | **0**（不开启） |
| DIR | **0**（从外设/ROM 读） | **1**（从存储器读，发往外设） |
| CPAR | **ROM 地址**（源） | **USART1->DR 地址**（目的） |
| CMAR | **RAM 地址**（目的） | **数组地址**（源） |
| PINC | **1**（ROM 地址自增） | **0**（串口地址不自增） |
| MINC | **1**（RAM 地址自增） | **1**（数组地址自增） |
| 通道 | **任意**（如通道 1） | **硬件固定**（通道 4） |
| 额外配置 | 无 | **USART1->CR3.DMAT = 1** |

---

## 三、DMA 通道分配（硬件固定）

### 3.1 USART 的 DMA 通道

| 串口 | TX 通道 | RX 通道 |
|------|:-------:|:-------:|
| **USART1** | **DMA1 Channel 4** | DMA1 Channel 5 |
| USART2 | DMA1 Channel 7 | DMA1 Channel 6 |
| USART3 | DMA1 Channel 2 | DMA1 Channel 3 |
| UART4 | DMA2 Channel 5 | DMA2 Channel 3 |
| UART5 | 无 DMA | 无 DMA |

> 通道分配由芯片硬件连线固定，不可更改。TX 和 RX 使用不同通道。

---

## 四、串口 DMA 使能（额外配置）

### 4.1 CR3 寄存器

```
USART1->CR3 中有两个 DMA 使能位：

DMAT（bit 7）：DMA 发送使能  ← 本实验使用
DMAR（bit 6）：DMA 接收使能

必须将 DMAT 置 1，否则 DMA 通道无法向 DR 写入数据
```

### 4.2 配置代码

```c
USART1->CR3 |= USART_CR3_DMAT;    // 使能串口 DMA 发送
```

---

## 五、数据方向分析

### 5.1 DIR 位配置

```
CCR.DIR = 0：从外设读（外设 → 存储器）
CCR.DIR = 1：从存储器读，发往外设（存储器 → 外设）← 本实验

本实验：从 RAM 数组读取数据 → 发送到 USART1 DR
  → 数据来源：存储器（RAM）
  → 数据去向：外设（USART1）
  → DIR = 1
```

### 5.2 为什么是写 TDR 而不是 RDR

```
从三二视角看发送和接收：
  → 发送：三二内部数据 → 串口 DR → TX 引脚 → 电脑
  → 接收：电脑 → RX 引脚 → 串口 DR → 三二内部存储器

本实验是发送：
  → RAM 数据通过 DMA → 写入 TDR
  → TDR 通过 TX 引脚发送出去

三二内部给串口传数据 = 写 TDR = 发送
不是接收！
```

---

## 六、地址自增分析

### 6.1 为什么串口地址不能自增

```
外设地址（CPAR）= USART1->DR 地址（固定）

每次传输都要往同一个 DR 寄存器写入数据
如果自增：地址会偏移到相邻寄存器（如 SR、BRR）
  → 写错寄存器 → 数据错误或功能异常

❌ 串口地址必须不自增
```

### 6.2 为什么存储器地址要自增

```
存储器地址（CMAR）= 数组首地址

数组在内存中连续存放：src[0], src[1], src[2], src[3]
每次传输一个字节后地址 +1
  → 取 src[0] 写入 DR
  → 取 src[1] 写入 DR
  → 取 src[2] 写入 DR
  → 取 src[3] 写入 DR

✅ 存储器地址必须自增
```

---

## 七、源和目的地址分配

```
CPAR（外设地址寄存器）= USART1->DR 地址（目的）
CMAR（存储器地址寄存器）= 数组首地址（源）

⚠️ 与存储器到存储器模式刚好相反！

存储器到存储器：
  CPAR = 源（ROM）
  CMAR = 目的（RAM）

内存到串口：
  CPAR = 目的（USART1->DR）
  CMAR = 源（数组）
```

---

## 八、CCR 寄存器配置汇总

| 配置项 | 位 | 宏定义 | 本实验值 | 说明 |
|--------|:--:|--------|:--------:|------|
| MEM2MEM | 14 | — | **0** | 不使用存储器到存储器 |
| PL[1:0] | 13:12 | — | 10 | 高优先级 |
| MSIZE[1:0] | 11:10 | — | **00** | 8 位 |
| PSIZE[1:0] | 9:8 | — | **00** | 8 位 |
| MINC | 7 | — | **1** | 存储器地址自增 |
| PINC | 6 | — | **0** | **外设地址不自增** |
| CIRC | 5 | — | 0 | 正常模式（可选循环） |
| DIR | 4 | — | **1** | **存储器→外设** |
| TEIE | 3 | — | 0 | — |
| HTIE | 2 | — | 0 | — |
| TCIE | 1 | — | **1** | 传输完成中断 |
| EN | 0 | — | 最后 | 通道使能 |

---

## 九、完整初始化代码

```c
void DMA1_Init(void)
{
    // ① 开启 DMA1 时钟
    RCC->AHBENR |= RCC_AHBENR_DMA1EN;

    // ② 传输方向：存储器→外设
    DMA1_Channel4->CCR |= DMA_CCR4_DIR;          // DIR = 1

    // ③ 数据宽度：8 位
    DMA1_Channel4->CCR &= ~DMA_CCR4_PSIZE;       // PSIZE = 00
    DMA1_Channel4->CCR &= ~DMA_CCR4_MSIZE;       // MSIZE = 00

    // ④ 地址自增：存储器自增，外设不自增
    DMA1_Channel4->CCR |=  DMA_CCR4_MINC;        // 存储器自增
    DMA1_Channel4->CCR &= ~DMA_CCR4_PINC;        // 外设不自增

    // ⑤ 传输完成中断
    DMA1_Channel4->CCR |= DMA_CCR4_TCIE;

    // ⑥ NVIC 配置
    NVIC_SetPriorityGrouping(3);
    NVIC_SetPriority(DMA1_Channel4_IRQn, 2);
    NVIC_EnableIRQ(DMA1_Channel4_IRQn);

    // ⑦ 使能串口 DMA 发送
    USART1->CR3 |= USART_CR3_DMAT;               // 额外配置！
}
```

---

## 十、数据传输函数

```c
void DMA1_Transmit(uint32_t src_addr, uint32_t dest_addr, uint16_t data_len)
{
    // ① 设置外设地址（目的 = USART1->DR）
    DMA1_Channel4->CPAR = dest_addr;

    // ② 设置存储器地址（源 = 数组首地址）
    DMA1_Channel4->CMAR = src_addr;

    // ③ 设置传输数据量
    DMA1_Channel4->CNDTR = data_len;

    // ④ 开启通道
    DMA1_Channel4->CCR |= DMA_CCR4_EN;
}
```

---

## 十一、中断服务函数

```c
volatile uint8_t is_finished = 0;

void DMA1_Channel4_IRQHandler(void)
{
    if (DMA1->ISR & DMA_ISR_TCIF4)           // 通道 4 传输完成
    {
        DMA1->IFCR |= DMA_IFCR_CTCIF4;       // 清除标志
        DMA1_Channel4->CCR &= ~DMA_CCR4_EN;  // 关闭通道
        is_finished = 1;
    }
}
```

---

## 十二、主函数实现

```c
#include "stm32f10x.h"
#include "usart.h"
#include "dma.h"
#include "delay.h"
#include <stdio.h>

// RAM 中的发送数据
uint8_t src[4] = {'a', 'b', 'c', 'd'};

int main(void)
{
    USART1_Init(115200);
    DMA1_Init();
    Delay_init();

    printf("Hello World!\n");
    Delay_ms(1);                              // 等待 printf 发送完成

    DMA1_Transmit((uint32_t)src,              // 源地址（RAM）
                  (uint32_t)&USART1->DR,      // 目的地址（串口 DR）
                  4);                         // 数据长度

    while (1)
    {
    }
}
```

### 12.1 地址传递说明

```c
// 源地址：数组名 = 首地址，强转为 uint32_t
(uint32_t)src

// 目的地址：取 USART1->DR 的地址，强转为 uint32_t
(uint32_t)&USART1->DR
```

---

## 十三、字符被吞的问题与解决

### 13.1 问题现象

```
printf("Hello World!\n");
DMA1_Transmit(src, &USART1->DR, 4);

期望输出：Hello World!
         abcd

实际输出：Hello World!abcd
         （缺少换行，\n 被吞了）
```

### 13.2 原因分析

```
① printf 通过 USART1->DR 逐字符发送
② 最后一个字符（\n）写入 TDR 后，尚未发送完成
③ DMA 通道立即开启，向 DR 写入 'a'
④ 'a' 覆盖了未发送完的 \n
⑤ \n 丢失

根本原因：
  DMA 速度极快，不检查 TDR 是否为空
  直接覆盖，导致前一个字符丢失
```

### 13.3 解决方案

```c
printf("Hello World!\n");
Delay_ms(1);                                  // 等待 printf 发送完成
DMA1_Transmit(src, &USART1->DR, 4);

// 或者更精确的方式：等待 TXE 标志位
// while (!(USART1->SR & USART_SR_TXE));
```

```
延迟时间估算：
  115200 波特率 → 1 字节 ≈ 87μs
  \n 发送完成需要约 87μs
  Delay_ms(1) = 1000μs >> 87μs，完全足够
  
  精确延迟：几十微秒即可
```

---

## 十四、循环模式（CIRC）

### 14.1 启用循环模式

```c
DMA1_Channel4->CCR |= DMA_CCR4_CIRC;    // CIRC = 1
```

### 14.2 循环模式行为

```
Normal 模式（CIRC=0）：
  CNDTR 减到 0 → 停止 → 产生 TC 事件
  串口输出：abcd（一次）

Circular 模式（CIRC=1）：
  CNDTR 减到 0 → CNDTR 自动重装为初始值
              → 地址自动回到起始
              → 继续发送 → 循环往复
  串口输出：abcdabcdabcdabcd...（不停刷屏）
```

### 14.3 循环模式下中断处理注意事项

```c
void DMA1_Channel4_IRQHandler(void)
{
    if (DMA1->ISR & DMA_ISR_TCIF4)
    {
        DMA1->IFCR |= DMA_IFCR_CTCIF4;

        // ⚠️ 循环模式下不要关闭通道！
        // DMA1_Channel4->CCR &= ~DMA_CCR4_EN;  // 不要这行！

        is_finished = 1;
    }
}
```

---

## 十五、寄存器配置流程总结

```
初始化：
  ① RCC->AHBENR |= DMA1EN              → 开 DMA 时钟
  ② CCR |= DIR                         → 存储器→外设
  ③ CCR &= ~PSIZE / ~MSIZE             → 8 位数据宽度
  ④ CCR |= MINC / CCR &= ~PINC         → 存储器自增，外设不自增
  ⑤ CCR |= TCIE                        → 传输完成中断
  ⑥ NVIC 配置                          → 优先级和使能
  ⑦ USART1->CR3 |= DMAT               → 串口 DMA 发送使能

传输：
  ① CPAR  = &USART1->DR               → 外设地址（目的）
  ② CMAR  = 数组首地址                 → 存储器地址（源）
  ③ CNDTR = 数据长度                   → 传输数量
  ④ CCR  |= EN                         → 开启传输

中断：
  ① 判断 ISR & TCIF4                   → 通道 4 传输完成
  ② IFCR |= CTCIF4                     → 清除标志
  ③ CCR &= ~EN                         → 关闭通道（Normal 模式）
```

---

## 十六、与存储器到存储器模式的完整对比

| 对比项 | 存储器到存储器 | 内存到串口 |
|--------|:-------------:|:---------:|
| MEM2MEM | 1 | **0** |
| DIR | 0 | **1** |
| CPAR（外设地址） | ROM 地址（源） | **USART1->DR（目的）** |
| CMAR（存储器地址） | RAM 地址（目的） | **数组地址（源）** |
| PINC | 1（ROM 自增） | **0（串口不自增）** |
| MINC | 1（RAM 自增） | **1（数组自增）** |
| 通道选择 | 任意 | **固定（通道 4）** |
| 额外配置 | 无 | **CR3.DMAT = 1** |
| 循环模式 | 无意义 | **可用** |
| 注意事项 | 无 | **吞字符问题** |

---

## 十七、常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 串口无输出 | 通道号错误 | 确认 DMA1 Channel 4 |
| 串口无输出 | CR3.DMAT 未开启 | `USART1->CR3 \|= DMAT` |
| 串口无输出 | CCR.DIR 配错 | DIR = 1（存储器→外设） |
| 字符被吞 | DMA 覆盖未发完的数据 | 发送前加延迟或等 TXE |
| 数据错误 | PINC 开启 | **串口地址不能自增** |
| CPAR/CMAR 写反 | 地址分配错误 | CPAR=DR，CMAR=数组 |
| 只发一次 | Normal 模式 | 开启 CIRC 循环模式 |
| 循环后关通道 | 中断中关闭了通道 | 循环模式下不关通道 |
| 编译报错 | 地址未强转 | `(uint32_t)&USART1->DR` |