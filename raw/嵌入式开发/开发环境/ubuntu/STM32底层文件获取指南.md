---
title: "STM32底层文件获取指南"
category: "STM32/开发环境"
tags: [CMSIS, 启动文件, 链接脚本, STM32CubeF1]
abstract: "介绍STM32F103底层开发文件的获取方式和在固件包中的路径"
source: "原创"
update_time: 2026-05-28
status: 完成
type: 实操
---

## 一句话定义

STM32F103底层开发所需的系统头文件、CMSIS内核文件、启动文件和链接脚本，主要来自STM32CubeF1固件包。

## 核心内容

### 一、获取固件包（总入口）

前往 ST 官网下载 **STM32CubeF1**：

```
https://www.st.com/en/embedded-software/stm32cubef1.html
```

下载解压后，你会得到类似这样的目录结构：

```
STM32Cube_FW_F1_V1.8.5/
├── Drivers/
│   ├── CMSIS/                    ← 核心文件在这里
│   └── STM32F1xx_HAL_Driver/     ← HAL/LL 驱动
├── Projects/                     ← 官方例程
├── Middlewares/
└── ...
```

### 二、逐文件对应路径

#### 1. 系统寄存器与启动配置

|文件|在固件包中的路径|
|---|---|
|`stm32f10x.h`|`Drivers/CMSIS/Device/ST/STM32F1xx/Include/stm32f10x.h`|
|`system_stm32f10x.c`|`Drivers/CMSIS/Device/ST/STM32F1xx/Source/Templates/system_stm32f10x.c`|
|`system_stm32f10x.h`|`Drivers/CMSIS/Device/ST/STM32F1xx/Include/system_stm32f10x.h`|

> **说明**：`stm32f10x.h` 是寄存器地址的宏定义，列出了该芯片所有外设寄存器。`system_stm32f10x.c` 包含 `SystemInit()` 函数，用于初始化时钟树。

#### 2. ARM Cortex-M3 内核文件（CMSIS）

|文件|在固件包中的路径|
|---|---|
|`core_cm3.h`|`Drivers/CMSIS/Include/core_cm3.h`|
|`core_cm3.c`|`Drivers/CMSIS/Include/core_cm3.c`（较新版本可能已合并到头文件中）|

> **说明**：CMSIS 是 ARM 官方标准，所有 Cortex-M3 芯片通用。提供 NVIC、SysTick、内核寄存器访问等基础功能。在较新版本的 CMSIS（v5+）中，`core_cm3.c` 可能不再单独存在，相关实现已内联到头文件。

#### 3. 启动文件

|文件|在固件包中的路径|
|---|---|
|`startup_stm32f103xe.s`|`Drivers/CMSIS/Device/ST/STM32F1xx/Source/Templates/gcc/startup_stm32f103xe.s`|

固件包中提供了多种工具链的启动文件：

```
Source/Templates/
├── arm/          ← Keil MDK 用 (.s)
├── gcc/          ← GCC (Makefile / STM32CubeIDE) 用 (.s)  ← 你要这个
├── iar/          ← IAR 用 (.s)
└── TASKING/      ← TASKING 编译器用
```

文件名中的 `xe` 代表中容量/大容量系列（512KB Flash 的 F103）。如果你用的是 F103C8T6（64KB），也可以用这个启动文件，或者用 `startup_stm32f103xb.s`。

#### 4. 链接脚本

|文件|来源|
|---|---|
|`STM32F103XX_FLASH.ld`|**不在固件包中**，需要手写或从 STM32CubeIDE 项目中导出|

**方式一：从 STM32CubeIDE 项目中获取**

```
STM32Cube_FW_F1_V1.8.5/Projects/STM32F103RB-Nucleo/Templates/
```

用 STM32CubeIDE 打开项目，编译后会自动生成 `.ld` 文件，位置在项目根目录。

**方式二：手写（最推荐，理解更深）**

```ld
/* STM32F103C8T6 为例：64KB Flash, 20KB SRAM */
MEMORY
{
    FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 64K
    RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 20K
}

SECTIONS
{
    .isr_vector : { . = ALIGN(4); KEEP(*(.isr_vector)) } > FLASH
    .text       : { *(.text*) } > FLASH
    .rodata     : { *(.rodata*) } > FLASH
    _sidata = LOADADDR(.data);
    .data : AT(_sidata) { _sdata = .; *(.data*) _edata = .; } > RAM
    .bss  : { _sbss = .; *(.bss*) _ebss = .; } > RAM
}
```

不同型号的 Flash/SRAM 大小：

|型号|Flash|RAM|
|---|---|---|
|F103C8T6|64K|20K|
|F103CBT6|128K|20K|
|F103RCT6|256K|48K|
|F103ZET6|512K|64K|

### 三、另一种更快的方式：STM32CubeMX 生成

1. 打开 STM32CubeMX
2. 选择芯片 **STM32F103C8Tx**
3. 配置时钟、引脚等
4. **Toolchain 选择 Makefile（或 STM32CubeIDE）**
5. 点击 Generate Code

生成的项目中，所有上述文件**都已经就位**，直接复制即可。

## 注意事项 & 踩坑

- 不同芯片型号的启动文件名不同（xb/xe），注意区分
- 链接脚本中的 Flash/RAM 大小必须与实际芯片匹配
- CMSIS 版本不同，文件结构可能有差异

## 相关笔记

- [[STM32寄存器开发概述]]
- [[STM32CubeMX安装笔记]]
- [[Makefile基础与进阶]]

## 参考来源

- STM32CubeF1 固件包
- STM32F103 参考手册
