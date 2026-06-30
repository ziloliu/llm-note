# DMA 存储器到存储器传输 — 寄存器方式实现 笔记

---

## 一、实验概述

| 项目 | 说明 |
|------|------|
| 传输方向 | **ROM（Flash）→ RAM（SRAM）** |
| DMA 控制器 | DMA1 |
| 通道 | **通道 1** |
| 数据宽度 | 8 位（1 字节） |
| 传输数据 | 4 个字节 |
| 传输方式 | 存储器到存储器（MEM2MEM） |

---

## 二、工程创建

### 2.1 文件结构

```
Project/
├── Hardware/
│   ├── DMA/
│   │   ├── dma.c          ← 新增
│   │   └── dma.h          ← 新增
│   └── USART/
│       ├── usart.c
│       └── usart.h
├── User/
│   ├── main.c
│   └── stm32f10x.h
└── ...
```

### 2.2 工程配置

```
① 新增 Hardware/DMA 组
② 添加 dma.c 到工程
③ Include Path 添加 DMA 目录
④ Debug: ST-Link, Reset and Run
```

---

## 三、关键寄存器访问方式

### 3.1 DMA 寄存器结构

```
DMA1 的寄存器分为两类：

① 所有通道共用（直接通过 DMA1-> 访问）：
   DMA1->ISR          中断状态（只读）
   DMA1->IFCR         中断标志清除（只写）

② 每个通道独立（通过 DMA1_Channelx-> 访问）：
   DMA1_Channel1->CCR    通道配置
   DMA1_Channel1->CNDTR  数据数量
   DMA1_Channel1->CPAR   外设地址
   DMA1_Channel1->CMAR   存储器地址
```

### 3.2 为什么这样设计

```
底层实现：用结构体定义 4 个通道寄存器
  → typedef struct { CCR, CNDTR, CPAR, CMAR } DMA_Channel_TypeDef;

每个通道用结构体指针指向不同基地址：
  DMA1_Channel1 → 通道 1 基地址
  DMA1_Channel2 → 通道 2 基地址
  ...

共用寄存器单独定义在 DMA_TypeDef 中：
  → ISR, IFCR

代码复用：同一套结构体定义，不用重复定义 CCR1/CCR2/...
```

### 3.3 访问方式对比

| 寄存器类型 | 访问方式 | 示例 |
|-----------|---------|------|
| 共用寄存器 | `DMA1->寄存器名` | `DMA1->ISR` |
| 通道寄存器 | `DMA1_Channelx->寄存器名` | `DMA1_Channel1->CCR` |
| 通道配置位 | `DMA_Channel1->CCR \|=` 位定义 | `DMA1_Channel1->CCR \|= DMA_CCR1_EN` |

---

## 四、CCR 寄存器配置详解

### 4.1 CCR 配置位与对应的库宏

| 配置项 | 位 | 宏定义 | 本实验值 | 说明 |
|--------|:--:|--------|:--------:|------|
| MEM2MEM | 14 | DMA_CCR1_MEM2MEM | **1** | 存储器到存储器 |
| PL[1:0] | 13:12 | DMA_CCR1_PL | 10 | 高优先级 |
| MSIZE[1:0] | 11:10 | DMA_CCR1_MSIZE | **00** | 8 位 |
| PSIZE[1:0] | 9:8 | DMA_CCR1_PSIZE | **00** | 8 位 |
| MINC | 7 | DMA_CCR1_MINC | **1** | 存储器地址自增 |
| PINC | 6 | DMA_CCR1_PINC | **1** | 外设地址自增 |
| CIRC | 5 | DMA_CCR1_CIRC | 0 | 正常模式 |
| DIR | 4 | DMA_CCR1_DIR | **0** | 从外设读 |
| TEIE | 3 | DMA_CCR1_TEIE | 0 | 传输错误中断 |
| HTIE | 2 | DMA_CCR1_HTIE | 0 | 传输过半中断 |
| TCIE | 1 | DMA_CCR1_TCIE | **1** | 传输完成中断 |
| EN | 0 | DMA_CCR1_EN | 最后 | 通道使能 |

### 4.2 各位配置代码

```c
// ① 存储器到存储器模式
DMA1_Channel1->CCR |= DMA_CCR1_MEM2MEM;

// ② 数据方向：从外设读（ROM → RAM）
DMA1_Channel1->CCR &= ~DMA_CCR1_DIR;      // DIR = 0（默认，可省略）

// ③ 数据宽度：8 位
DMA1_Channel1->CCR &= ~DMA_CCR1_PSIZE;    // PSIZE = 00
DMA1_Channel1->CCR &= ~DMA_CCR1_MSIZE;    // MSIZE = 00

// ④ 地址自增
DMA1_Channel1->CCR |= DMA_CCR1_PINC;      // 外设地址自增
DMA1_Channel1->CCR |= DMA_CCR1_MINC;      // 存储器地址自增

// ⑤ 传输完成中断
DMA1_Channel1->CCR |= DMA_CCR1_TCIE;      // TCIE = 1
```

---

## 五、DMA 初始化函数

```c
void DMA1_Init(void)
{
    // ① 开启 DMA1 时钟（AHB 总线）
    RCC->AHBENR |= RCC_AHBENR_DMA1EN;

    // ② 存储器到存储器模式
    DMA1_Channel1->CCR |= DMA_CCR1_MEM2MEM;

    // ③ 从外设读（ROM 当作外设）
    DMA1_Channel1->CCR &= ~DMA_CCR1_DIR;

    // ④ 数据宽度 8 位
    DMA1_Channel1->CCR &= ~DMA_CCR1_PSIZE;
    DMA1_Channel1->CCR &= ~DMA_CCR1_MSIZE;

    // ⑤ 地址自增
    DMA1_Channel1->CCR |= DMA_CCR1_PINC;
    DMA1_Channel1->CCR |= DMA_CCR1_MINC;

    // ⑥ 传输完成中断使能
    DMA1_Channel1->CCR |= DMA_CCR1_TCIE;

    // ⑦ NVIC 配置
    NVIC_SetPriorityGrouping(3);
    NVIC_SetPriority(DMA1_Channel1_IRQn, 2);
    NVIC_EnableIRQ(DMA1_Channel1_IRQn);
}
```

---

## 六、DMA 数据传输函数

```c
void DMA1_Transmit(uint32_t src_addr, uint32_t dest_addr, uint16_t data_len)
{
    // ① 设置源地址（ROM，当作"外设"）
    DMA1_Channel1->CPAR = src_addr;

    // ② 设置目标地址（RAM）
    DMA1_Channel1->CMAR = dest_addr;

    // ③ 设置传输数据量
    DMA1_Channel1->CNDTR = data_len;

    // ④ 开启通道，开始传输
    DMA1_Channel1->CCR |= DMA_CCR1_EN;
}
```

### 6.1 函数参数说明

| 参数 | 类型 | 说明 | 对应寄存器 |
|------|------|------|-----------|
| src_addr | uint32_t | 源地址（ROM） | CPAR |
| dest_addr | uint32_t | 目标地址（RAM） | CMAR |
| data_len | uint16_t | 数据长度 | CNDTR |

### 6.2 配置顺序

```
⚠️ 地址和数据量必须在通道使能（EN=1）之前配置

正确顺序：
  ① CPAR = 源地址
  ② CMAR = 目标地址
  ③ CNDTR = 数据量
  ④ CCR |= EN（开启通道，立即开始传输）

开启通道后数据立即开始传输！
```

---

## 七、中断服务函数

```c
volatile uint8_t is_finished = 0;

void DMA1_Channel1_IRQHandler(void)
{
    // ① 判断传输完成标志
    if (DMA1->ISR & DMA_ISR_TCIF1)
    {
        // ② 清除中断标志（写 IFCR，不是写 ISR）
        DMA1->IFCR |= DMA_IFCR_CTCIF1;

        // ③ 关闭 DMA 通道
        DMA1_Channel1->CCR &= ~DMA_CCR1_EN;

        // ④ 通知主函数
        is_finished = 1;
    }
}
```

### 7.1 关键点

| 操作 | 寄存器 | 说明 |
|------|--------|------|
| 判断标志 | DMA1->ISR | 只读，不能直接清除 |
| 清除标志 | DMA1->IFCR | **写 1 清除**对应标志 |
| 关闭通道 | DMA1_Channel1->CCR | EN 位清零 |

### 7.2 ISR 与 IFCR 对应关系

| ISR（只读） | IFCR（写 1 清除） |
|:-----------:|:-----------------:|
| GIF1 | CGIF1 |
| TCIF1 | **CTCIF1** |
| HTIF1 | CHTIF1 |
| TEIF1 | CTEIF1 |

---

## 八、头文件声明

### 8.1 dma.h

```c
#ifndef __DMA_H
#define __DMA_H

#include "stm32f10x.h"

extern volatile uint8_t is_finished;

void DMA1_Init(void);
void DMA1_Transmit(uint32_t src_addr, uint32_t dest_addr, uint16_t data_len);

#endif
```

---

## 九、主函数实现

```c
#include "stm32f10x.h"
#include "usart.h"
#include "dma.h"
#include <stdio.h>

// 全局常量（存放在 ROM/Flash）
const uint8_t source[4] = {12, 13, 14, 10};

// 全局变量（存放在 RAM/SRAM）
uint8_t dest[4] = {0, 0, 0, 0};

int main(void)
{
    USART1_Init(115200);
    DMA1_Init();

    printf("Hello World!\n");

    // 打印地址验证 ROM 和 RAM 位置
    printf("dest addr:   %p\n", dest);
    printf("source addr: %p\n", source);

    // 开启 DMA 传输
    DMA1_Transmit((uint32_t)source, (uint32_t)dest, 4);

    while (1)
    {
        if (is_finished)
        {
            is_finished = 0;

            // 验证传输结果
            printf("%d\t%d\t%d\t%d\n",
                   dest[0], dest[1], dest[2], dest[3]);
        }
    }
}
```

### 9.1 地址类型转换

```c
// 数组名 = 首地址（uint8_t* 类型）
// CPAR/CMAR 是 32 位寄存器
// 需要强转为 uint32_t
DMA1_Transmit((uint32_t)source, (uint32_t)dest, 4);
```

---

## 十、运行结果

```
Hello World!
dest addr:   0x20000001      ← RAM 地址
source addr: 0x080008B0      ← ROM 地址
12    13    14    10         ← DMA 传输成功
```

### 10.1 地址验证

```
ROM（Flash）地址范围：0x08000000 起
RAM（SRAM）地址范围：0x20000000 起

source（const）→ 0x0800xxxx → ROM ✅
dest（变量）    → 0x2000xxxx → RAM ✅

地址差距巨大，确认是不同存储模块
```

---

## 十一、CCR 配置与寄存器对照

| CubeMX 概念 | 寄存器位 | 宏定义 | 本实验值 |
|-------------|---------|--------|:--------:|
| MEM2MEM | CCR[14] | DMA_CCR1_MEM2MEM | 1 |
| DIR | CCR[4] | DMA_CCR1_DIR | 0 |
| PSIZE | CCR[9:8] | DMA_CCR1_PSIZE | 00 |
| MSIZE | CCR[11:10] | DMA_CCR1_MSIZE | 00 |
| PINC | CCR[6] | DMA_CCR1_PINC | 1 |
| MINC | CCR[7] | DMA_CCR1_MINC | 1 |
| PL | CCR[13:12] | DMA_CCR1_PL | 10 |
| CIRC | CCR[5] | DMA_CCR1_CIRC | 0 |
| TCIE | CCR[1] | DMA_CCR1_TCIE | 1 |
| HTIE | CCR[2] | DMA_CCR1_HTIE | 0 |
| TEIE | CCR[3] | DMA_CCR1_TEIE | 0 |
| EN | CCR[0] | DMA_CCR1_EN | 最后置 1 |

---

## 十二、完整配置流程总结

```
初始化（DMA1_Init）：
  ① RCC->AHBENR |= DMA1EN           → 开时钟
  ② CCR |= MEM2MEM                   → 存储器到存储器
  ③ CCR &= ~DIR                      → 从外设（ROM）读
  ④ CCR &= ~PSIZE / ~MSIZE           → 8 位数据宽度
  ⑤ CCR |= PINC / MINC               → 地址自增
  ⑥ CCR |= TCIE                      → 传输完成中断
  ⑦ NVIC 配置                        → 中断优先级和使能

传输（DMA1_Transmit）：
  ① CPAR  = src_addr                 → 源地址（ROM）
  ② CMAR  = dest_addr                → 目标地址（RAM）
  ③ CNDTR = data_len                 → 数据数量
  ④ CCR  |= EN                       → 开启传输

中断（DMA1_Channel1_IRQHandler）：
  ① 判断 ISR & TCIF1                 → 传输完成？
  ② IFCR |= CTCIF1                   → 清除标志
  ③ CCR &= ~EN                       → 关闭通道
  ④ is_finished = 1                   → 通知主函数
```

---

## 十三、常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 传输无结果 | 时钟未开启 | RCC->AHBENR \|= DMA1EN |
| 传输无结果 | CPAR/CMAR 地址写反 | CPAR=源(RAM 中 const)，CMAR=目标(RAM 中变量) |
| 传输无结果 | 通道未使能 | CCR \|= EN 放在最后 |
| 中断不进 | TCIE 未开启 | CCR \|= TCIE |
| 中断不进 | NVIC 未配置 | NVIC_EnableIRQ |
| 反复进中断 | 标志未清除 | IFCR \|= CTCIF1 |
| 地址强转错误 | 类型不匹配 | `(uint32_t)array_name` |
| 数据宽度不匹配 | PSIZE/MSIZE 不一致 | 设为相同值 |
| ROM 数据错误 | 变量未加 const | `const uint8_t source[]` |

---

## 十四、DMA 传输数据量对照

| CNDTR 值 | PSIZE | 传输总量 | 说明 |
|:---------:|:-----:|:--------:|------|
| 4 | 8 位 | 4 字节 | 本实验 |
| 4 | 16 位 | 8 字节 | 每次传 2 字节 |
| 4 | 32 位 | 16 字节 | 每次传 4 字节 |
| 100 | 8 位 | 100 字节 | 大量数据传输 |
| 65535 | 8 位 | 65535 字节 | 最大值 |

---

## 十五、存储器映像验证

```
Keil 魔法棒 → Target 选项卡：

IROM1（Flash/ROM）：
  起始地址：0x08000000
  大小：根据芯片型号

IRAM1（SRAM/RAM）：
  起始地址：0x20000000
  大小：根据芯片型号（如 64KB）

source（const）→ 0x0800xxxx → 在 IROM1 范围内 ✅
dest（变量）    → 0x2000xxxx → 在 IRAM1 范围内 ✅
```