# ADC 独立模式多通道采集（DMA方式）— 寄存器实现 笔记

---

## 一、实验概述

| 项目 | 说明 |
|------|------|
| 功能 | 双通道模拟信号采集，串口打印 |
| ADC 模块 | ADC1（独立模式） |
| 通道 | 通道 10（PC0）+ 通道 12（PC2） |
| 工作模式 | 扫描模式 + 连续转换 + 软件触发 |
| 数据传输 | **DMA1 通道 1** |
| 数据宽度 | **16 位**（12位精度存于16位寄存器） |

---

## 二、为什么多通道需要 DMA

### 2.1 单通道 vs 多通道的区别

| 对比项 | 单通道 | 多通道 |
|--------|:------:|:------:|
| SCAN 模式 | 禁用（0） | **开启（1）** |
| CONT 模式 | 开启（单曲循环） | 开启（列表循环） |
| L 值 | 0（1个通道） | **1（2个通道）** |
| SQR 排列 | 只有 SQ1 | SQ1 + SQ2 |
| DR 覆盖风险 | 无（只转一个） | **有（多个通道共用1个DR）** |
| 数据传输方式 | 直接读 DR | **必须用 DMA** |

### 2.2 EOC 标志在多通道时的问题

```
单通道时：
  每转换一次 → 产生一次 EOC
  → 及时读取 DR，不会被覆盖

多通道时（扫描模式）：
  整组转换完成后 → 才产生一次 EOC
  → 中间各通道转换结果会互相覆盖 DR
  → 判断 EOC 来不及及时取走每个通道的数据

解决方案：DMA 通道
  → 每次 DR 有数据就自动通过 DMA 传输到内存
  → 速度远快于 AD 转换速度
  → 不会覆盖
```

### 2.3 DMA 通道分配

```
ADC1 对应的 DMA 通道：DMA1 Channel 1（硬件固定）

查表确认：
  DMA1 通道 1 → ADC1
  DMA1 通道 1 → TIM2_CH3（共享，但本实验用 ADC1）
```

---

## 三、多通道配置与单通道的差异

### 3.1 需要修改的配置项

| 配置项 | 单通道值 | 多通道值 | 说明 |
|--------|:--------:|:--------:|------|
| CR1.SCAN | 0 | **1** | 开启扫描模式 |
| CR2.CONT | 1 | 1 | 连续转换（不变） |
| SQR1.L | 0 | **1** | 2 个通道（L+1=2） |
| SQR3.SQ1 | 10 | 10 | 第 1 个通道（不变） |
| SQR3.SQ2 | — | **12** | 第 2 个通道（新增） |
| SMPR1.SMP10 | 001 | 001 | 通道 10 采样时间（不变） |
| SMPR1.SMP12 | — | **001** | 通道 12 采样时间（新增） |
| CR2.DMA | 0 | **1** | 开启 DMA 模式 |
| DMA CCR | — | **大量配置** | DMA 通道配置（新增） |

---

## 四、新增通道的寄存器配置

### 4.1 开启扫描模式

```c
// CR1.SCAN = 1（多通道必须开启）
ADC1->CR1 |= ADC_CR1_SCAN;
```

```
SCAN = 0：只转换序列中第一个通道（单曲播放）
SCAN = 1：按序列顺序依次转换所有通道（顺序播放）
```

### 4.2 序列长度 L

```c
// SQR1[23:20] = L = 1（2 个通道：L+1=2）
ADC1->SQR1 &= ~(0xF << 20);   // 清零 L
ADC1->SQR1 |= (0x1 << 20);    // L = 1
```

```
L = 0：1 个通道
L = 1：2 个通道 ← 本实验
L = 15：16 个通道
```

### 4.3 通道 12 保存到序列

```c
// SQR3[9:5] = SQ2 = 12（第 2 个转换的通道）
ADC1->SQR3 &= ~(0x1F << 5);   // 清零 SQ2 的 5 位
ADC1->SQR3 |= (12 << 5);      // SQ2 = 通道 12
```

```
SQR3 位分配：
  [4:0]   = SQ1 = 10（第 1 个转换）← 通道 10
  [9:5]   = SQ2 = 12（第 2 个转换）← 通道 12
  [14:10] = SQ3
  ...
```

### 4.4 通道 12 采样时间

```c
// SMPR1[5:3] = SMP12 = 001（7.5 周期）
ADC1->SMPR1 &= ~(0x7 << 3);   // 清零 SMP12
ADC1->SMPR1 |= (0x1 << 3);    // SMP12 = 001
```

```
SMPR1 位分配：
  [2:0]   = SMP10 ← 通道 10（已配）
  [5:3]   = SMP12 ← 通道 12（新增）
  ...
```

### 4.5 开启 ADC DMA 模式

```c
// CR2.DMA = 1（开启 DMA 请求）
ADC1->CR2 |= ADC_CR2_DMA;
```

---

## 五、DMA 通道配置（核心新增部分）

### 5.1 开启 DMA 时钟

```c
RCC->AHBENR |= RCC_AHBENR_DMA1EN;
```

### 5.2 DMA CCR 寄存器配置

```c
// ① 传输方向：外设→存储器
DMA1_Channel1->CCR &= ~DMA_CCR1_DIR;    // DIR = 0

// ② 数据宽度：16 位
DMA1_Channel1->CCR |=  (0x1 << 8);      // PSIZE = 01
DMA1_Channel1->CCR |=  (0x1 << 10);     // MSIZE = 01

// ③ 地址自增：外设不增，存储器自增
DMA1_Channel1->CCR &= ~DMA_CCR1_PINC;   // PINC = 0（DR 地址固定）
DMA1_Channel1->CCR |=  DMA_CCR1_MINC;   // MINC = 1（数组地址自增）

// ④ 循环模式
DMA1_Channel1->CCR |= DMA_CCR1_CIRC;    // CIRC = 1
```

### 5.3 各配置项详解

**传输方向**
```
DIR = 0：从外设读 → 写入存储器
  → 外设 = ADC1->DR（数据来源）
  → 存储器 = 内存数组（数据去向）
```

**数据宽度**
```
为什么配 16 位（不是 8 位）？
  → ADC 精度 12 位
  → 数据寄存器 DR 是 16 位
  → DMA 传输的数据宽度应与 DR 一致 = 16 位

PSIZE = MSIZE = 01（16 位）
  00 = 8 位
  01 = 16 位 ← 本实验
  10 = 32 位
```

**地址自增**
```
PINC = 0（外设不自增）：
  → 外设是 ADC1->DR，地址固定
  → 每次都从同一个 DR 地址取数据
  → 不需要自增

MINC = 1（存储器自增）：
  → 存储器是数组，地址连续
  → data[0] 存通道 10 结果
  → data[1] 存通道 12 结果
  → 需要自增才能依次存入
```

**循环模式**
```
DMA CIRC = 1（循环传输）：
  → 配合 ADC CONT = 1（连续转换）
  → ADC 不停转换 → DMA 不停传输
  → 实时捕获信号变化

匹配关系：
  ADC 单次 + DMA 单次 → 转一次就停
  ADC 连续 + DMA 单次 → DR 会覆盖，DMA 不管
  ADC 连续 + DMA 循环 → 完美配合 ✅
```

### 5.4 DMA 地址和数据量配置

```c
// ⑤ 外设地址（源 = ADC1->DR）
DMA1_Channel1->CPAR = (uint32_t)&ADC1->DR;

// ⑥ 存储器地址（目的 = 数组首地址）
DMA1_Channel1->CMAR = dest_addr;         // 由参数传入

// ⑦ 数据量
DMA1_Channel1->CNDTR = data_len;         // 由参数传入（2）
```

### 5.5 DMA 通道使能

```c
// ⑧ 开启 DMA 通道（必须在 ADC 上电之后！）
DMA1_Channel1->CCR |= DMA_CCR1_EN;
```

---

## 六、启动顺序（关键！）

### 6.1 正确顺序

```c
void ADC1_DMA_StartConvert(uint32_t dest_addr, uint8_t data_len)
{
    // ① DMA 配置：地址和数据量
    DMA1_Channel1->CPAR  = (uint32_t)&ADC1->DR;
    DMA1_Channel1->CMAR  = dest_addr;
    DMA1_Channel1->CNDTR = data_len;

    // ② ADC 上电唤醒（必须先于 DMA 使能！）
    ADC1->CR2 |= ADC_CR2_ADON;

    // ③ DMA 通道使能（ADC 上电后再开启）
    DMA1_Channel1->CCR |= DMA_CCR1_EN;

    // ④ 校准
    ADC1->CR2 |= ADC_CR2_CAL;
    while (ADC1->CR2 & ADC_CR2_CAL);

    // ⑤ 启动转换
    ADC1->CR2 |= ADC_CR2_ADON;          // 再次写 1 启动
}
```

### 6.2 顺序错误的后果

```
错误顺序：先开 DMA 使能 → 再 ADC 上电

问题：
  → ADC 模块处于断电状态
  → DMA 通道无法建立有效的数据传输
  → 转换结果无法通过 DMA 传输到内存
  → 主函数中读取的数据始终为 0

原因：
  → DMA 建立通道时需要检测到有效信号
  → ADC 断电时 DR 无有效信号
  → DMA 通道建立失败

解决方案（二选一）：
  ① 先 ADC 上电 → 再 DMA 使能（调整顺序）
  ② 开启 GPIO 时钟（提供时钟信号，DMA 可建立通道）
```

### 6.3 两种解决方案对比

| 方案 | 操作 | 说明 |
|------|------|------|
| 方案一 | ADC 先上电，再 DMA 使能 | **推荐**，逻辑清晰 |
| 方案二 | 开启 GPIOC 时钟 | 提供时钟信号，DMA 可建立通道 |

```c
// 方案二：开启 GPIOC 时钟
RCC->APB2ENR |= RCC_APB2ENR_IOPCEN;
// → 即使 DMA 先于 ADC 上电，也能正常工作
// → 因为 GPIO 时钟信号可供 DMA 检测
```

---

## 七、GPIO 配置

### 7.1 PC0（通道 10）

```c
GPIOC->CRL &= ~(0xF << 0);   // PC0 = 模拟输入
```

### 7.2 PC2（通道 12）

```c
GPIOC->CRL &= ~(0xF << 8);   // PC2 = 模拟输入
```

```
模拟输入不需要 GPIO 时钟
  → 一根导线直连 ADC 输入
  → 不需要施密特触发器、上下拉等电路
  → 但开启时钟可以避免 DMA 建立通道问题
```

---

## 八、头文件 adc.h

```c
#ifndef __ADC_H
#define __ADC_H

#include "stm32f10x.h"

void ADC1_Init(void);
void ADC1_DMA_Init(void);
void ADC1_DMA_StartConvert(uint32_t dest_addr, uint8_t data_len);

#endif
```

---

## 九、主函数实现

```c
#include "stm32f10x.h"
#include "usart.h"
#include "adc.h"
#include "delay.h"
#include <stdio.h>

// 保存两个通道转换结果的数组
uint16_t data[2] = {0, 0};

int main(void)
{
    USART1_Init(115200);
    Delay_init();
    ADC1_Init();
    ADC1_DMA_Init();

    printf("Hello World!\n");

    // 启动 DMA 方式的 ADC 转换
    ADC1_DMA_StartConvert((uint32_t)data, 2);

    while (1)
    {
        // 打印两个通道的电压值
        printf("可变电阻(ADC10): %.2f V\t", data[0] * 3.3 / 4095);
        printf("PC2(ADC12): %.2f V\n", data[1] * 3.3 / 4095);
        Delay_ms(1000);
    }
}
```

---

## 十、运行结果

```
Hello World!
可变电阻(ADC10): 2.03 V    PC2(ADC12): 3.29 V
可变电阻(ADC10): 3.00 V    PC2(ADC12): 3.29 V
可变电阻(ADC10): 0.00 V    PC2(ADC12): 3.29 V
```

```
通道 10（PC0）→ 可变电阻 → 0V ~ 3.3V 随旋钮变化
通道 12（PC2）→ 接 3.3V  → 约 3.29V（跳线连接有损耗）

浮空输入时：
  → 会受周围环境影响
  → 随可变电阻变化而漂移
  → 约 1.64V 左右
```

---

## 十一、DMA 配置与 ADC 配置的匹配关系

| ADC 配置 | DMA 配置 | 匹配关系 |
|----------|----------|---------|
| CONT = 1（连续转换） | CIRC = 1（循环传输） | ✅ 完美配合 |
| CONT = 1（连续转换） | CIRC = 0（单次传输） | ❌ DMA 停了 ADC 还在转 |
| CONT = 0（单次转换） | CIRC = 0（单次传输） | ✅ 转一次就停 |
| PSIZE = 16 位 | PSIZE = 16 位 | ✅ 数据宽度一致 |
| MSIZE = 16 位 | MSIZE = 16 位 | ✅ 数据宽度一致 |

---

## 十二、完整配置流程

```
ADC 初始化（ADC1_Init）：
  ① RCC->APB2ENR |= ADC1EN           → 开 ADC 时钟
  ② RCC->CFGR |= ADCPRE_DIV6         → 72MHz/6 = 12MHz
  ③ GPIOC->CRL &= ~(0xF << 0)        → PC0 模拟输入
  ④ GPIOC->CRL &= ~(0xF << 8)        → PC2 模拟输入
  ⑤ CR1 |= SCAN                       → 开启扫描模式
  ⑥ CR2 |= CONT                       → 连续转换
  ⑦ CR2 &= ~ALIGN                     → 右对齐
  ⑧ SMPR1 |= 0x1                      → 通道 10 采样 7.5 周期
  ⑨ SMPR1 |= (0x1 << 3)              → 通道 12 采样 7.5 周期
  ⑩ SQR1 |= (0x1 << 20)              → L = 1（2 个通道）
  ⑪ SQR3 |= 10                        → SQ1 = 通道 10
  ⑫ SQR3 |= (12 << 5)                → SQ2 = 通道 12
  ⑬ CR2 |= EXTTRIG                    → 外部触发使能
  ⑭ CR2 |= EXTSEL                     → 软件触发（111）

DMA 初始化（ADC1_DMA_Init）：
  ① RCC->AHBENR |= DMA1EN            → 开 DMA 时钟
  ② CCR &= ~DIR                       → 外设→存储器
  ③ CCR |= PSIZE=01                   → 外设数据宽度 16 位
  ④ CCR |= MSIZE=01                   → 存储器数据宽度 16 位
  ⑤ CCR &= ~PINC                      → 外设地址不自增
  ⑥ CCR |= MINC                       → 存储器地址自增
  ⑦ CCR |= CIRC                       → 循环传输模式
  ⑧ CR2 |= DMA                        → ADC 开启 DMA 模式

启动（ADC1_DMA_StartConvert）：
  ① CPAR = &ADC1->DR                  → 外设地址
  ② CMAR = dest_addr                  → 存储器地址
  ③ CNDTR = data_len                  → 数据量
  ④ CR2 |= ADON                       → ADC 上电唤醒
  ⑤ CCR |= EN                         → DMA 通道使能
  ⑥ CR2 |= CAL                        → 校准
  ⑦ while(CR2 & CAL)                  → 等待校准完成
  ⑧ CR2 |= ADON                       → 启动转换
```

---

## 十三、新增寄存器配置汇总

### 13.1 与单通道相比新增的配置

| 寄存器 | 位 | 值 | 说明 |
|--------|:--:|:--:|------|
| CR1 | SCAN | **1** | 开启扫描模式 |
| SQR1[23:20] | L | **1** | 2 个通道 |
| SQR3[9:5] | SQ2 | **12** | 第 2 个通道 = 通道 12 |
| SMPR1[5:3] | SMP12 | **001** | 通道 12 采样时间 |
| CR2 | DMA | **1** | 开启 ADC DMA 模式 |
| DMA1 CCR | 多位 | — | DMA 通道配置 |
| DMA1 CPAR | — | &ADC1->DR | 外设地址 |
| DMA1 CMAR | — | 数组地址 | 存储器地址 |
| DMA1 CNDTR | — | 2 | 数据量 |

### 13.2 DMA CCR 配置汇总

| 位 | 名称 | 值 | 说明 |
|:--:|------|:--:|------|
| 4 | DIR | 0 | 外设→存储器 |
| 9:8 | PSIZE | 01 | 外设 16 位 |
| 11:10 | MSIZE | 01 | 存储器 16 位 |
| 6 | PINC | 0 | 外设地址不自增 |
| 7 | MINC | 1 | 存储器地址自增 |
| 5 | CIRC | 1 | 循环模式 |
| 0 | EN | 最后 | 通道使能 |

---

## 十四、GPIO 时钟的两种方案

### 14.1 方案一：不开启 GPIO 时钟 + 调整启动顺序

```c
// 不开启 GPIOC 时钟
// 必须先 ADC 上电 → 再 DMA 使能
ADC1->CR2 |= ADC_CR2_ADON;              // 先上电
DMA1_Channel1->CCR |= DMA_CCR1_EN;      // 再使能 DMA
```

### 14.2 方案二：开启 GPIO 时钟

```c
// 开启 GPIOC 时钟
RCC->APB2ENR |= RCC_APB2ENR_IOPCEN;
// DMA 可以检测到时钟信号，建立通道
// 不受启动顺序影响
```

### 14.3 建议

```
实际项目中建议：
  → 用到哪个 GPIO 就开启哪个 GPIO 时钟
  → 避免后续出现各种莫名其妙的问题
  → 多开一点时钟对功耗影响很小
```

---

## 十五、浮空输入问题

```
PC2 悬空（不接任何信号）时：
  → 电压约 1.64V（不稳定）
  → 会随周围环境变化
  → 会随可变电阻调节而漂移

原因：
  → 悬空引脚相当于天线
  → 会感应周围的电磁干扰
  → 没有确定的电位

解决：
  → 接确定的信号源
  → 或配置上下拉电阻
```

---

## 十六、常见问题

| 问题          | 原因            | 解决                       |
| ----------- | ------------- | ------------------------ |
| 主函数无输出      | DMA 未传回数据     | 检查启动顺序                   |
| DMA 不工作     | ADC 未上电就开 DMA | 先 ADON 再 DMA EN          |
| DMA 不工作     | GPIO 时钟未开     | 开启 GPIOC 时钟              |
| 数据全为 0      | 通道号配错         | 检查 SQR3 中 SQ1=10, SQ2=12 |
| 数据全为 4095   | 通道号配重         | SQ1 和 SQ2 不同             |
| 两通道数据一样     | SQ1=SQ2 配成相同  | 检查通道号                    |
| 数据宽度不匹配     | DMA PSIZE≠16  | 确认 PSIZE=MSIZE=01        |
| 浮空引脚数据漂移    | 未接信号源         | 接确定信号或配置上下拉              |
| 最大电压不到 3.3V | 未校准           | 添加 CAL 校准步骤              |