# FSMC 扩展外部 SRAM 寄存器方式 —— 超详细笔记

---

## 一、实验背景与目标

### 1.1 什么是 FSMC

**FSMC**（Flexible Static Memory Controller，灵活的静态存储器控制器）是 STM32 内部的一个外设。它的作用是：

- 把 CPU 发出的**内部总线访问**，自动转换成**外部存储器所需的时序协议**（如 SRAM、NOR Flash、NAND Flash、PC Card 等）。
- 配置好之后，CPU 或 DMA 就可以像访问内部内存一样，直接读写外部存储器，**不需要手动写读写函数**。

### 1.2 本实验目标

使用 **寄存器方式**（不依赖标准库的 FSMC_Init 函数），配置 FSMC 扩展一个外部 SRAM 芯片 **IS62WV51216**（512K × 16bit = 1MB）。

- 芯片容量：512K × 16 位 = 1M 字节
- 数据宽度：16 位
- 使用 FSMC 的 **Bank1 第 3 个存储块**（片选 NE3）
- 映射地址：`0x68000000` 开始

### 1.3 为什么用寄存器方式

- 标准库函数封装较深，不利于理解底层原理。
- 寄存器方式能看清每一位的含义，掌握 FSMC 的工作机制。
- 代码更直接，便于移植和调试。

---

## 二、工程创建与配置

### 2.1 复制工程

1. 复制之前的 `hardware` 工程文件夹。
2. 重命名为 `fsmc_sram_register`。
3. 打开 Keil 工程，修改工程名。

### 2.2 新建文件

在 `hardware` 目录下新建文件夹 `fsmc`，内部创建：

- `fsmc.c` —— 存放 FSMC 初始化代码
- `fsmc.h` —— 存放函数声明

### 2.3 Keil 工程配置

1. 点击"小方块"（Manage Project Items）。
2. 添加目录：`hardware/fsmc`。
3. 添加文件：选择 `fsmc.c`。
4. 在 C/C++ 选项卡中，Include Paths 勾选 `hardware/fsmc`。
5. 在 Debug 选项卡中：
   - 勾选 `Reset and Run`
   - 去掉 `Enable`（避免调试时自动运行）

---

## 三、FSMC 初始化代码框架

### 3.1 fsmc.h

```c
#ifndef __FSMC_H
#define __FSMC_H

#include "stm32f10x.h"

void FSMC_Init(void);

#endif
```

### 3.2 fsmc.c 主流程

```c
#include "fsmc.h"

void FSMC_GPIO_Init(void);   // 内部函数声明

void FSMC_Init(void)
{
    FSMC_GPIO_Init();        // 第一步：配置 GPIO 工作模式
    // 第二步：配置 FSMC 寄存器（BCR + BTR）
}
```

> **关键理解**：FSMC 配置好后，就像建立了一条"通道"。CPU 或 DMA 通过这条通道，把内部总线访问自动转换成外部存储器协议。所以**只需要一个初始化函数**，不需要定义读/写函数。

---

## 四、时钟开启

### 4.1 FSMC 时钟

FSMC 挂在 **AHB 总线**上：

```c
RCC_AHBPeriphClockCmd(RCC_AHBPeriph_FSMC, ENABLE);
```

或者直接操作寄存器：

```c
RCC->AHBENR |= RCC_AHBENR_FSMCEN;
```

### 4.2 GPIO 时钟

本实验用到了 **PD、PE、PF、PG** 四组 GPIO，都挂在 **APB2 高速外设总线**上：

```c
RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOD |
                       RCC_APB2Periph_GPIOE |
                       RCC_APB2Periph_GPIOF |
                       RCC_APB2Periph_GPIOG, ENABLE);
```

或直接操作寄存器：

```c
RCC->APB2ENR |= RCC_APB2ENR_IOPDEN |
                RCC_APB2ENR_IOPEEN |
                RCC_APB2ENR_IOPFEN |
                RCC_APB2ENR_IOPGEN;
```

> **注意**：虽然这些引脚用的是复用功能，但复用功能仍然需要 GPIO 模块内部的电路参与，所以 GPIO 时钟必须开。

---

## 五、GPIO 工作模式配置（最繁琐的部分）

### 5.1 引脚分类总览

| 类型 | 引脚 | 对应 FSMC 信号 | 说明 |
|------|------|----------------|------|
| 地址线 A0~A5 | PF0~PF5 | FSMC_A0~A5 | 低地址 |
| 地址线 A6~A9 | PF12~PF15 | FSMC_A6~A9 | 中地址 |
| 地址线 A10~A15 | PG0~PG5 | FSMC_A10~A15 | 高地址 |
| 地址线 A16~A18 | PD11~PD13 | FSMC_A16~A18 | 最高地址 |
| 数据线 D0~D1 | PD14~PD15 | FSMC_D0~D1 | 数据低 2 位 |
| 数据线 D2~D3 | PD0~PD1 | FSMC_D2~D3 | 数据 |
| 数据线 D4~D12 | PE7~PE15 | FSMC_D4~D12 | 数据 |
| 数据线 D13~D15 | PD8~PD10 | FSMC_D13~D15 | 数据高 3 位 |
| 读使能 | PD4 | FSMC_NOE | Output Enable |
| 写使能 | PD5 | FSMC_NWE | Write Enable |
| 低字节屏蔽 | PE0 | FSMC_NBL0 | Byte Lane 0 |
| 高字节屏蔽 | PE1 | FSMC_NBL1 | Byte Lane 1 |
| 片选 | PG10 | FSMC_NE3 | Chip Select |

### 5.2 工作模式统一配置

所有引脚统一配置为：

- **复用推挽输出**（Alternate Function Push-Pull）
- MODE = `11`（输出模式，最大 50MHz）
- CNF = `10`（复用推挽）

**为什么数据线也配成输出？**
因为配置成输出后，输入通道仍然有效，所以数据线可以双向使用，不需要单独配成输入。

### 5.3 配置方法：分组操作

#### 5.3.1 地址线 PF0~PF5（使用 CRL）

```c
// 配置 MODE 为 11（输出，50MHz）
GPIOF->CRL |= (0x3 << 0)  | (0x3 << 4)  | (0x3 << 8)  |
              (0x3 << 12) | (0x3 << 16) | (0x3 << 20);

// 配置 CNF 高位为 1
GPIOF->CRL |= (0x1 << 2)  | (0x1 << 6)  | (0x1 << 10) |
              (0x1 << 14) | (0x1 << 18) | (0x1 << 22);

// 配置 CNF 低位为 0
GPIOF->CRL &= ~((0x1 << 0) | (0x1 << 4) | (0x1 << 8) |
                (0x1 << 12) | (0x1 << 16) | (0x1 << 20));
```

#### 5.3.2 地址线 PF12~PF15（使用 CRH）

```c
// MODE 11
GPIOF->CRH |= (0x3 << 16) | (0x3 << 20) | (0x3 << 24) | (0x3 << 28);
// CNF 高位 1
GPIOF->CRH |= (0x1 << 18) | (0x1 << 22) | (0x1 << 26) | (0x1 << 30);
// CNF 低位 0
GPIOF->CRH &= ~((0x1 << 16) | (0x1 << 20) | (0x1 << 24) | (0x1 << 28));
```

#### 5.3.3 地址线 PG0~PG5

与 PF0~PF5 类似，只需把 `GPIOF` 改成 `GPIOG`。

#### 5.3.4 地址线 PD11~PD13（使用 CRH）

```c
GPIOD->CRH |= (0x3 << 12) | (0x3 << 16) | (0x3 << 20);   // MODE
GPIOD->CRH |= (0x1 << 14) | (0x1 << 18) | (0x1 << 22);   // CNF 高位
GPIOD->CRH &= ~((0x1 << 12) | (0x1 << 16) | (0x1 << 20)); // CNF 低位
```

#### 5.3.5 数据线 PD0~PD1、PD8~PD10、PD14~PD15

按同样规则分组配置，分别使用 CRL 和 CRH。

#### 5.3.6 数据线 PE7~PE15

使用 `GPIOE->CRL`（PE7）和 `GPIOE->CRH`（PE8~PE15）。

#### 5.3.7 控制信号

```c
// PD4 (NOE) 和 PD5 (NWE)
GPIOD->CRL |= (0x3 << 16) | (0x3 << 20);   // MODE
GPIOD->CRL |= (0x1 << 18) | (0x1 << 22);   // CNF 高位
GPIOD->CRL &= ~((0x1 << 16) | (0x1 << 20)); // CNF 低位

// PE0 (NBL0) 和 PE1 (NBL1)
GPIOE->CRL |= (0x3 << 0) | (0x3 << 4);     // MODE
GPIOE->CRL |= (0x1 << 2) | (0x1 << 6);     // CNF 高位
GPIOE->CRL &= ~((0x1 << 0) | (0x1 << 4));  // CNF 低位

// PG10 (NE3)
GPIOG->CRH |= (0x3 << 8);                  // MODE
GPIOG->CRH |= (0x1 << 10);                 // CNF 高位
GPIOG->CRH &= ~(0x1 << 8);                 // CNF 低位
```

> **提示**：这部分工作非常枯燥，但必须耐心完成。建议自己敲一遍，不要直接复制，加深理解。

---

## 六、FSMC 寄存器详细配置

### 6.1 寄存器映射关系

FSMC 的 Bank1 有 4 个存储块，每个存储块有两个寄存器：

| 存储块 | 片选 | BCR 寄存器 | BTR 寄存器 |
|--------|------|------------|------------|
| Bank1 块0 | NE1 | FSMC_BCR1 → BTCR[0] | FSMC_BTR1 → BTCR[1] |
| Bank1 块1 | NE2 | FSMC_BCR2 → BTCR[2] | FSMC_BTR2 → BTCR[3] |
| Bank1 块2 | NE3 | FSMC_BCR3 → BTCR[4] | FSMC_BTR3 → BTCR[5] |
| Bank1 块3 | NE4 | FSMC_BCR4 → BTCR[6] | FSMC_BTR4 → BTCR[7] |

本实验用的是 **NE3**，所以：

- `FSMC_BCR3` 对应 `FSMC_Bank1->BTCR[4]`
- `FSMC_BTR3` 对应 `FSMC_Bank1->BTCR[5]`

### 6.2 BCR3 配置（存储块控制寄存器）

| 位 | 名称 | 值 | 说明 |
|----|------|----|------|
| MBKEN | 存储块使能 | 1 | 开启 Bank |
| MUXEN | 地址数据复用 | 0 | 不复用（SRAM 通常不复用） |
| MTYP | 存储器类型 | 00 | SRAM/ROM |
| MWID | 数据宽度 | 01 | 16 位 |
| FACCEN | 闪存访问使能 | 0 | 禁止（SRAM 不需要） |
| WREN | 写使能 | 1 | 开启 |
| WAITEN | 等待使能 | 0 | 不使用等待信号 |
| ASYNCWAIT | 异步等待 | 0 | 不使用 |

```c
// 6.2.1 存储块使能
FSMC_Bank1->BTCR[4] |= FSMC_BCR3_MBKEN;

// 6.2.2 存储器类型 = SRAM（00）
FSMC_Bank1->BTCR[4] &= ~FSMC_BCR3_MTYP;

// 6.2.3 禁止闪存访问
FSMC_Bank1->BTCR[4] &= ~FSMC_BCR3_FACCEN;

// 6.2.4 数据宽度 = 16 位（01）
FSMC_Bank1->BTCR[4] &= ~FSMC_BCR3_MWID;   // 高位清零
FSMC_Bank1->BTCR[4] |= FSMC_BCR3_MWID_0;  // 低位置 1

// 6.2.5 地址数据不复用
FSMC_Bank1->BTCR[4] &= ~FSMC_BCR3_MUXEN;

// 6.2.6 写使能开启
FSMC_Bank1->BTCR[4] |= FSMC_BCR3_WREN;
```

### 6.3 BTR3 配置（存储块时序寄存器）

| 位 | 名称 | 值 | 说明 |
|----|------|----|------|
| ADDSET | 地址建立时间 | 0 | 最小 1 个 HCLK 周期 |
| ADDHLD | 地址保持时间 | 0 | 仅复用模式使用 |
| DATAST | 数据建立时间 | 0x71 << 8 | 约 1μs |
| BUSTURN | 总线恢复时间 | 0 | 默认 |
| CLKDIV | 时钟分频 | 0 | 同步模式使用 |
| DATLAT | 数据延迟 | 0 | 同步模式使用 |
| ACCMOD | 访问模式 | 0 | 模式 A |

```c
// 6.3.1 地址建立时间 = 0（最小 1 周期）
FSMC_Bank1->BTCR[5] &= ~FSMC_BTR3_ADDSET;

// 6.3.2 数据建立时间清零后赋值
FSMC_Bank1->BTCR[5] &= ~FSMC_BTR3_DATAST;
FSMC_Bank1->BTCR[5] |= (0x71 << 8);   // DATAST 占 15:8 位
```

> **DATAST 位说明**：DATAST 占据 BTR 的 bit15~bit8，共 8 位。写入时要左移 8 位。`0x71` = 113 个 HCLK 周期，若 HCLK = 72MHz，约 1.57μs，满足 SRAM 时序要求。

---

## 七、主函数测试

### 7.1 方法一：`__attribute__((at(...)))` 指定全局变量地址

```c
uint8_t v1 __attribute__((at(0x68000000)));
uint8_t v2 __attribute__((at(0x68000004)));
uint8_t v3 = 30;   // 普通全局变量，位于片内 SRAM
```

**语法说明**：

- `__attribute__` 是 GCC 编译器的扩展关键字，标准 C 没有。
- `at(...)` 指定变量存放的绝对地址。
- 地址必须是 **4 的整数倍**（32 位系统对齐要求）。

**局限性**：

- 只能用于**全局变量**，局部变量无法指定。
- 地址必须 4 字节对齐，否则编译报错。
- 语法比较特殊，可读性差。

### 7.2 方法二：指针直接访问（推荐）

```c
uint8_t *p = (uint8_t *)0x68000001;
*p = 100;
printf("value=%d, addr=%p\n", *p, p);
```

**优点**：

- 无对齐限制，任意地址都可以。
- 使用灵活，可以在运行时动态改变。
- 标准库源码中就是用这种方式访问寄存器的。

### 7.3 测试代码完整示例

```c
int main(void)
{
    // 初始化 FSMC
    FSMC_Init();

    // 方法一：全局变量指定地址
    v1 = 10;
    v2 = 20;

    // 方法二：指针访问
    uint8_t *p = (uint8_t *)0x68000001;
    *p = 100;

    // 打印验证
    printf("v1 value=%d, addr=%p\n", v1, &v1);
    printf("v2 value=%d, addr=%p\n", v2, &v2);
    printf("v3 value=%d, addr=%p\n", v3, &v3);
    printf("p  value=%d, addr=%p\n", *p, p);

    while(1);
}
```

### 7.4 测试结果分析

| 变量 | 值 | 地址 | 所在区域 |
|------|----|------|----------|
| v1 | 10 | 0x68000000 | 外部 SRAM |
| v2 | 20 | 0x68000004 | 外部 SRAM |
| v3 | 30 | 0x2000xxxx | 片内 SRAM |
| p | 100 | 0x68000001 | 外部 SRAM |

- `0x68000000` 开头 → 外部 SRAM（FSMC Bank1 NE3 映射区）
- `0x20000000` 开头 → 片内 SRAM

> **结论**：v1、v2、p 确实存放在了外部 SRAM 中，说明 FSMC 配置成功。

---

## 八、关键知识点总结

### 8.1 FSMC 地址映射

| Bank | 片选 | 起始地址 | 大小 |
|------|------|----------|------|
| Bank1 块0 | NE1 | 0x60000000 | 64MB |
| Bank1 块1 | NE2 | 0x64000000 | 64MB |
| Bank1 块2 | NE3 | 0x68000000 | 64MB |
| Bank1 块3 | NE4 | 0x6C000000 | 64MB |

### 8.2 GPIO 配置要点

- 所有 FSMC 引脚统一配置为**复用推挽输出**。
- MODE = 11，CNF = 10。
- 低 8 位用 CRL，高 8 位用 CRH。
- 每个引脚占 4 位：2 位 MODE + 2 位 CNF。

### 8.3 FSMC 配置要点

- BCR 配置存储块属性（类型、宽度、使能等）。
- BTR 配置读写时序（地址建立、数据建立时间）。
- 配置完成后，外部 SRAM 就像普通内存一样被访问。

### 8.4 两种地址指定方式对比

| 方式 | 语法 | 限制 | 推荐度 |
|------|------|------|--------|
| `__attribute__((at()))` | 编译期指定 | 仅全局变量，4 字节对齐 | 一般 |
| 指针访问 | 运行时指定 | 无 | 推荐 |

### 8.5 常见问题

**Q1：为什么数据线也配成输出？**
A：配置成输出后，输入通道仍然有效，所以数据线可以双向使用。

**Q2：为什么地址必须 4 字节对齐？**
A：32 位系统要求变量地址按 4 字节对齐，否则访问效率降低甚至出错。

**Q3：局部变量能指定地址吗？**
A：不能。局部变量在运行时由系统自动分配，编译期无法指定。

**Q4：什么时候变量会放到外部 SRAM？**
A：当片内 SRAM 不够用时，系统会自动扩展到外部 SRAM。但这个过程不可控，测试时不好验证。

---

## 九、完整代码清单

### fsmc.h

```c
#ifndef __FSMC_H
#define __FSMC_H

#include "stm32f10x.h"

void FSMC_Init(void);

#endif
```

### fsmc.c

```c
#include "fsmc.h"

void FSMC_GPIO_Init(void)
{
    // 开启时钟
    RCC->AHBENR |= RCC_AHBENR_FSMCEN;
    RCC->APB2ENR |= RCC_APB2ENR_IOPDEN | RCC_APB2ENR_IOPEEN |
                    RCC_APB2ENR_IOPFEN | RCC_APB2ENR_IOPGEN;

    // 配置地址线 PF0~PF5
    GPIOF->CRL |= (0x3 << 0)  | (0x3 << 4)  | (0x3 << 8)  |
                  (0x3 << 12) | (0x3 << 16) | (0x3 << 20);
    GPIOF->CRL |= (0x1 << 2)  | (0x1 << 6)  | (0x1 << 10) |
                  (0x1 << 14) | (0x1 << 18) | (0x1 << 22);
    GPIOF->CRL &= ~((0x1 << 0) | (0x1 << 4) | (0x1 << 8) |
                    (0x1 << 12) | (0x1 << 16) | (0x1 << 20));

    // 配置地址线 PF12~PF15
    GPIOF->CRH |= (0x3 << 16) | (0x3 << 20) | (0x3 << 24) | (0x3 << 28);
    GPIOF->CRH |= (0x1 << 18) | (0x1 << 22) | (0x1 << 26) | (0x1 << 30);
    GPIOF->CRH &= ~((0x1 << 16) | (0x1 << 20) | (0x1 << 24) | (0x1 << 28));

    // 配置地址线 PG0~PG5
    GPIOG->CRL |= (0x3 << 0)  | (0x3 << 4)  | (0x3 << 8)  |
                  (0x3 << 12) | (0x3 << 16) | (0x3 << 20);
    GPIOG->CRL |= (0x1 << 2)  | (0x1 << 6)  | (0x1 << 10) |
                  (0x1 << 14) | (0x1 << 18) | (0x1 << 22);
    GPIOG->CRL &= ~((0x1 << 0) | (0x1 << 4) | (0x1 << 8) |
                    (0x1 << 12) | (0x1 << 16) | (0x1 << 20));

    // 配置地址线 PD11~PD13
    GPIOD->CRH |= (0x3 << 12) | (0x3 << 16) | (0x3 << 20);
    GPIOD->CRH |= (0x1 << 14) | (0x1 << 18) | (0x1 << 22);
    GPIOD->CRH &= ~((0x1 << 12) | (0x1 << 16) | (0x1 << 20));

    // 配置数据线 PD0~PD1、PD8~PD10、PD14~PD15（略，按同样规则）
    // 配置数据线 PE7~PE15（略，按同样规则）

    // 配置控制信号 PD4(NOE)、PD5(NWE)
    GPIOD->CRL |= (0x3 << 16) | (0x3 << 20);
    GPIOD->CRL |= (0x1 << 18) | (0x1 << 22);
    GPIOD->CRL &= ~((0x1 << 16) | (0x1 << 20));

    // 配置 PE0(NBL0)、PE1(NBL1)
    GPIOE->CRL |= (0x3 << 0) | (0x3 << 4);
    GPIOE->CRL |= (0x1 << 2) | (0x1 << 6);
    GPIOE->CRL &= ~((0x1 << 0) | (0x1 << 4));

    // 配置 PG10(NE3)
    GPIOG->CRH |= (0x3 << 8);
    GPIOG->CRH |= (0x1 << 10);
    GPIOG->CRH &= ~(0x1 << 8);
}

void FSMC_Init(void)
{
    FSMC_GPIO_Init();

    // 配置 BCR3
    FSMC_Bank1->BTCR[4] |= FSMC_BCR3_MBKEN;      // 使能
    FSMC_Bank1->BTCR[4] &= ~FSMC_BCR3_MTYP;      // SRAM
    FSMC_Bank1->BTCR[4] &= ~FSMC_BCR3_FACCEN;    // 禁止闪存
    FSMC_Bank1->BTCR[4] &= ~FSMC_BCR3_MWID;      // 清高位
    FSMC_Bank1->BTCR[4] |= FSMC_BCR3_MWID_0;     // 16 位
    FSMC_Bank1->BTCR[4] &= ~FSMC_BCR3_MUXEN;     // 不复用
    FSMC_Bank1->BTCR[4] |= FSMC_BCR3_WREN;       // 写使能

    // 配置 BTR3
    FSMC_Bank1->BTCR[5] &= ~FSMC_BTR3_ADDSET;    // 地址建立 = 0
    FSMC_Bank1->BTCR[5] &= ~FSMC_BTR3_DATAST;    // 清零
    FSMC_Bank1->BTCR[5] |= (0x71 << 8);          // 数据建立 = 0x71
}
```

### main.c

```c
#include "stm32f10x.h"
#include "fsmc.h"
#include <stdio.h>

uint8_t v1 __attribute__((at(0x68000000)));
uint8_t v2 __attribute__((at(0x68000004)));
uint8_t v3 = 30;

int main(void)
{
    FSMC_Init();

    v1 = 10;
    v2 = 20;

    uint8_t *p = (uint8_t *)0x68000001;
    *p = 100;

    printf("v1 value=%d, addr=%p\n", v1, &v1);
    printf("v2 value=%d, addr=%p\n", v2, &v2);
    printf("v3 value=%d, addr=%p\n", v3, &v3);
    printf("p  value=%d, addr=%p\n", *p, p);

    while(1);
}
```

---

## 十、实验流程图

```
开始
  │
  ├─ 开启 FSMC 时钟（AHB）
  ├─ 开启 GPIO 时钟（APB2：PD/PE/PF/PG）
  │
  ├─ 配置 GPIO 工作模式
  │     ├─ 地址线（PD/PF/PG）
  │     ├─ 数据线（PD/PE）
  │     └─ 控制线（PD4/PD5/PE0/PE1/PG10）
  │
  ├─ 配置 FSMC BCR3
  │     ├─ 使能存储块
  │     ├─ 类型 = SRAM
  │     ├─ 宽度 = 16 位
  │     ├─ 不复用
  │     └─ 写使能
  │
  ├─ 配置 FSMC BTR3
  │     ├─ 地址建立时间
  │     └─ 数据建立时间
  │
  └─ 测试验证
        ├─ 方法一：__attribute__((at()))
        └─ 方法二：指针访问
```

