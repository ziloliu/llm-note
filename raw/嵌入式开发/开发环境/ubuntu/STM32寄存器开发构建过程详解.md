---
title: "STM32寄存器开发构建过程详解"
category: "STM32/开发环境"
tags: [构建过程, 预处理, 编译, 链接, 烧录]
abstract: "详解STM32寄存器开发从源代码到烧录的完整构建过程"
source: "原创"
update_time: 2026-05-28
status: 完成
type: 原理
---

## 一句话定义

STM32寄存器开发的构建过程包括预处理、编译、链接、格式转换和烧录五个阶段，最终将C代码转换为芯片可执行的机器码。

## 核心内容

### 全景流程图

```
                     源代码
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       main.c    startup.s    stm32f103xb.h
          │            │            │
          │            │     (预处理器展开)
          ▼            │            │
     ┌─────────┐       │            │
     │ 预处理器  │◄──────┘────────────┘
     │ (cpp)   │
     └────┬────┘
          │  main.i  (纯C，无宏/无#include)
          ▼
     ┌─────────┐
     │  编译器   │
     │ (cc1)   │
     └────┬────┘
          │  main.s  (ARM汇编)
          ▼
     ┌─────────┐
     │  汇编器   │
     │  (as)   │
     └────┬────┘
          │  main.o  (ELF目标文件，机器码，符号未解析)
          ▼
     ┌─────────┐
     │  链接器   │◄── 链接脚本(.ld) + 启动文件.o + 标准库
     │  (ld)   │
     └────┬────┘
          │  firmware.elf  (完整的ELF可执行文件)
          ▼
     ┌─────────┐
     │ objcopy  │
     └────┬────┘
          │  firmware.bin  (纯二进制，烧录用)
          │  firmware.hex  (Intel HEX格式)
          ▼
        烧录到芯片
```

### 第一阶段：预处理（Preprocessing）

```bash
arm-none-eabi-gcc -E main.c -o main.i
```

**做什么：**

把所有 `#include`、`#define`、`#ifdef`、宏替换等全部展开，生成一个纯 C 文件。

```c
// =========== 你写的 main.c ===========
#include "stm32f1xx.h"

int main(void) {
    RCC->APB2ENR |= RCC_APB2ENR_IOPAEN;
    GPIOA->CRL = 0x33333333;
}
```

```c
// =========== 预处理后的 main.i（简化示意）==========
// ---- 从 stm32f1xx.h 展开 ----

// 芯片识别
#define STM32F1  1
#define STM32F103xB  1
// ...（几千行）

// ---- 从 core_cm3.h 展开 ----
// Cortex-M3 核心寄存器定义
typedef struct {
    volatile uint32_t ISER[8];
    // ...
} NVIC_Type;
#define NVIC ((NVIC_Type *)0xE000E100UL)
// ...（几百行）

// ---- 从 stm32f103xb.h 展开 ----

// 基地址定义
#define PERIPH_BASE        0x40000000UL
#define APB2PERIPH_BASE    (PERIPH_BASE + 0x10000UL)
#define GPIOA_BASE         (APB2PERIPH_BASE + 0x0800UL)
#define RCC_BASE           (APB2PERIPH_BASE + 0x1000UL)

// 寄存器结构体
typedef struct {
    volatile uint32_t CRL;
    volatile uint32_t CRH;
    volatile uint32_t IDR;
    volatile uint32_t ODR;
    volatile uint32_t BSRR;
    volatile uint32_t BRR;
    volatile uint32_t LCKR;
} GPIO_TypeDef;

typedef struct {
    volatile uint32_t CR;
    volatile uint32_t CFGR;
    volatile uint32_t CIR;
    volatile uint32_t APB2RSTR;
    volatile uint32_t APB1RSTR;
    volatile uint32_t AHBENR;
    volatile uint32_t APB2ENR;    // ← 你要操作的寄存器
    volatile uint32_t APB1ENR;
    // ...
} RCC_TypeDef;

// 外设实例指针
#define GPIOA  ((GPIO_TypeDef *) 0x40010800UL)
#define RCC    ((RCC_TypeDef *)  0x40021000UL)

// 寄存器位定义
#define RCC_APB2ENR_IOPAEN_Pos   2U
#define RCC_APB2ENR_IOPAEN_Msk   (0x1UL << 2U)
#define RCC_APB2ENR_IOPAEN       RCC_APB2ENR_IOPAEN_Msk

// ---- 你的 main 函数（宏已全部替换）----
int main(void) {
    // RCC->APB2ENR |= RCC_APB2ENR_IOPAEN
    // 展开为:
    (*((volatile uint32_t *)(0x40021000UL + 0x18UL))) |= (0x1UL << 2U);

    // GPIOA->CRL = 0x33333333
    // 展开为:
    (*((volatile uint32_t *)(0x40010800UL + 0x00UL))) = 0x33333333;
}
```

**关键点：**

- `volatile` 确保编译器不会优化掉寄存器读写
- 所有外设操作最终变成了**对固定地址的内存读写**
- `__IO` 就是 `volatile` 的宏别名

### 第二阶段：编译（Compilation）

```bash
arm-none-eabi-gcc -mcpu=cortex-m3 -mthumb -c main.c -o main.o
arm-none-eabi-gcc -mcpu=cortex-m3 -mthumb -c startup_stm32f103xb.s -o startup.o
```

**做什么：**

将 C 代码编译为 ARM Cortex-M3 的 Thumb-2 指令集汇编，再汇编为机器码，打包成 ELF 目标文件。

```bash
# 查看生成的汇编（调试用）
arm-none-eabi-gcc -S -mcpu=cortex-m3 -mthumb -O1 main.c -o main.s
```

```asm
@ main.s（编译 main 函数的输出，简化示意）
main:
    @ RCC->APB2ENR |= RCC_APB2ENR_IOPAEN
    ldr     r0, =0x40021018      @ RCC->APB2ENR 地址 (0x40021000 + 0x18)
    ldr     r1, [r0]             @ 读 APB2ENR 当前值
    orr     r1, r1, #4           @ 置 bit2 (IOPAEN)
    str     r1, [r0]             @ 写回

    @ GPIOA->CRL = 0x33333333
    ldr     r0, =0x40010800      @ GPIOA->CRL 地址
    ldr     r1, =0x33333333
    str     r1, [r0]             @ 写入

loop:
    b       loop                 @ 死循环
```

**`-mcpu=cortex-m3 -mthumb` 的含义：**

```
-mcpu=cortex-m3    → 告诉编译器目标CPU是Cortex-M3
                      (影响指令调度、可用寄存器、流水线优化)

-mthumb            → 生成 Thumb-2 指令集代码
                      (ARM Cortex-M 系列只支持 Thumb，不支持 ARM 指令集)
```

### 第三阶段：链接（Linking）

```bash
arm-none-eabi-gcc \
    -mcpu=cortex-m3 -mthumb \
    -T STM32F103C8Tx_FLASH.ld \
    -Wl,--gc-sections \
    -specs=nosys.specs \
    startup.o main.o system_stm32f1xx.o \
    -o firmware.elf
```

**做什么：**

把多个 `.o` 文件合并，根据链接脚本分配地址，生成完整的可执行 ELF 文件。

#### 链接脚本做了什么

```ld
/* STM32F103C8Tx_FLASH.ld（简化示意） */

MEMORY
{
    FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 64K    /* 程序存储 */
    RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 20K    /* 运行内存 */
}

SECTIONS
{
    /* 中断向量表 —— 必须放在 Flash 最前面 */
    .isr_vector :
    {
        . = ALIGN(4);
        KEEP(*(.isr_vector))    /* 来自 startup.s 的 .isr_vector 段 */
        . = ALIGN(4);
    } >FLASH

    /* 程序代码 */
    .text :
    {
        . = ALIGN(4);
        *(.text)                /* 所有 .o 的代码段 */
        *(.text*)
        *(.rodata)              /* 只读数据、常量 */
        . = ALIGN(4);
        _etext = .;
    } >FLASH

    /* 已初始化的全局变量（存在Flash，启动时拷贝到RAM） */
    _sidata = LOADADDR(.data);
    .data :
    {
        . = ALIGN(4);
        _sdata = .;
        *(.data)
        *(.data*)
        . = ALIGN(4);
        _edata = .;
    } >RAM AT> FLASH

    /* 未初始化的全局变量（启动时清零） */
    .bss :
    {
        . = ALIGN(4);
        _sbss = .;
        *(.bss)
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
        _ebss = .;
    } >RAM
}
```

#### 内存布局

```
    Flash (0x0800_0000)                RAM (0x2000_0000)
    ┌─────────────────┐               ┌─────────────────┐
    │  中断向量表       │               │  .data 拷贝      │ ← 启动代码从Flash
    │  .isr_vector     │               │  (已初始化变量)    │   拷贝到这里
    ├─────────────────┤               ├─────────────────┤
    │  .text           │               │  .bss            │ ← 启动代码清零
    │  (程序代码)       │               │  (未初始化变量)    │
    ├─────────────────┤               ├─────────────────┤
    │  .rodata         │               │                  │
    │  (常量)           │               │  (栈空间 ↓)       │
    ├─────────────────┤               │         ↓        │
    │  .data 初始值     │ ──拷贝到──→   │  栈顶 (0x20005000)│
    └─────────────────┘               └─────────────────┘
```

### 第四阶段：生成可烧录文件

```bash
# ELF → 纯二进制（烧录用）
arm-none-eabi-objcopy -O binary firmware.elf firmware.bin

# ELF → Intel HEX（另一种烧录格式）
arm-none-eabi-objcopy -O ihex firmware.elf firmware.hex
```

```
firmware.bin vs firmware.elf 的区别:

firmware.elf:
┌──────────────┬────────────────────────────────┐
│ ELF 头        │ 元数据：入口地址、段表、符号表     │
│ Section: .text│ 代码机器码                      │
│ Section: .data│ 初始化变量的初始值               │
│ Section: .bss │ （不占空间，仅记录大小）          │
│ 符号表         │ 函数名、变量名、地址映射（调试用） │
└──────────────┴────────────────────────────────┘

firmware.bin:
┌──────────────────────────────────────────────┐
│ 纯机器码，从 0x0800_0000 开始顺序排列           │
│ 没有任何元数据，直接写入 Flash 即可              │
└──────────────────────────────────────────────┘
```

### 第五阶段：烧录

```bash
# 方式1：st-flash
st-flash write firmware.bin 0x08000000

# 方式2：OpenOCD
openocd -f interface/stlink.cfg -f target/stm32f1x.cfg \
    -c "program firmware.elf verify reset exit"
```

**烧录过程（以 OpenOCD 为例）:**

```
PC                           ST-Link                    STM32
 │                             │                          │
 │  USB: 连接 ST-Link          │                          │
 ├────────────────────────────>│                          │
 │                             │  SWD: 连接目标芯片         │
 │                             ├─────────────────────────>│
 │                             │                          │
 │  发送 firmware.bin          │                          │
 ├────────────────────────────>│  解锁 Flash               │
 │                             ├─────────────────────────>│
 │                             │                          │ Flash 解锁
 │                             │<─────────────────────────┤
 │                             │                          │
 │                             │  按 Page 擦除 Flash       │
 │                             ├─────────────────────────>│
 │                             │                          │ 擦除完成
 │                             │<─────────────────────────┤
 │                             │                          │
 │                             │  逐字写入 bin 数据         │
 │                             ├─────────────────────────>│
 │                             │                          │ 写入完成
 │                             │<─────────────────────────┤
 │                             │                          │
 │                             │  读回校验                 │
 │                             ├─────────────────────────>│
 │                             │  对比数据一致 ✓            │
 │                             │<─────────────────────────┤
 │                             │                          │
 │                             │  发送复位信号              │
 │                             ├─────────────────────────>│
 │                             │                          │ 芯片复位
 │                             │                          │ 从0x08000000开始执行
 烧录完成 ✓
```

### 一句话总结每个阶段

|阶段|输入|输出|核心工作|
|---|---|---|---|
|**预处理**|`.c` + `.h`|`.i`|展开 `#include`、宏替换|
|**编译**|`.i`|`.s` → `.o`|C 转 ARM 汇编，再转机器码|
|**链接**|多个 `.o` + `.ld`|`.elf`|合并文件，分配地址，解析符号|
|**objcopy**|`.elf`|`.bin` / `.hex`|去掉元数据，生成纯机器码|
|**烧录**|`.bin`|Flash 写入|通过 SWD 协议写入芯片 Flash|

整个过程的核心思想：**你写的 `RCC->APB2ENR |= (1<<2)` 最终变成了对地址 `0x40021018` 的一次 Load-OR-Store 操作，这三行汇编就被烧进了 Flash 的 `0x08000000` 起始位置，上电后 Cortex-M3 从向量表取出栈指针和复位地址，然后逐条执行。**

## 注意事项 & 踩坑

- 预处理后的 `.i` 文件可能非常大（几万行），包含所有头文件展开内容
- 链接脚本必须与芯片型号匹配，否则内存地址会错
- 烧录前确保芯片已解锁，否则写入失败

## 相关笔记

- [[STM32寄存器开发概述]]
- [[Makefile基础与进阶]]
- [[STM32调试指南]]

## 参考来源

- ARM Cortex-M3 技术参考手册
- STM32F103 参考手册
