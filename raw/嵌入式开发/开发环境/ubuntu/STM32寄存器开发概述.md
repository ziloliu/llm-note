---
title: "STM32寄存器开发概述"
category: "STM32/开发环境"
tags: [寄存器开发, 工具链, 交叉编译, CMSIS]
abstract: "介绍Ubuntu上STM32寄存器级开发的主流工具链和工程结构"
source: "原创"
update_time: 2026-05-28
status: 完成
type: 总结
---

## 一句话定义

Ubuntu上进行STM32寄存器级开发的主流方式是使用arm-none-eabi-gcc交叉编译器 + Makefile构建系统 + OpenOCD烧录调试。

## 核心内容

### 工具链概览

```
┌──────────┐    ┌──────────────┐    ┌────────────┐    ┌──────────┐
│  编辑器   │───>│ arm-none-eabi │───>│  烧录工具   │───>│ 调试器    │
│ VS Code  │    │    -gcc      │    │ OpenOCD    │    │ GDB      │
│ Vim/NeoVim│    │    -gdb      │    │ st-flash   │    │ OpenOCD  │
└──────────┘    └──────────────┘    └────────────┘    └──────────┘
     │
     ▼
┌──────────────────────────┐
│  构建系统: Makefile/CMake │
│  寄存器定义: CMSIS头文件   │
└──────────────────────────┘
```

### [安装工具链](Cooked/STM32/开发环境/ubuntu/ARM工具链安装与配置)


### 工程目录结构

```
REGISTER-TEST/
├── Makefile                   # 编译脚本 (需更新路径)
├── README.md                  # 项目说明文档
├── .gitignore                 # Git 忽略文件 (忽略编译产物)
├── build/                     # (自动生成) 存放编译过程中的 .o 和 .d 文件
├── output/                    # (自动生成) 存放最终生成的 .elf, .bin, .hex
│
├── app/                       # 用户业务逻辑代码
│   ├── main.c                 # 主程序入口
│   ├── gpio.c                 # (示例) 你自己封装的 GPIO 功能
│   ├── timer.c                # (示例) 你自己封装的 定时器 功能
│   └── inc/                   # 用户头文件
│       ├── main.h
│       ├── gpio.h
│       └── timer.h
│
├── system/                    # STM32 底层寄存器/系统文件 (官方提供，一般不修改)
│   ├── stm32f10x.h            # STM32F103 寄存器定义
│   ├── system_stm32f10x.c     # 系统时钟配置实现
│   └── system_stm32f10x.h
│
├── cmsis/                     # ARM Cortex-M 内核核心文件 (通常是通用的)
│   ├── core_cm3.h
│   └── core_cm3.c
│
├── startup/                   # 芯片启动文件
│   └── startup_stm32f103xe.s
│
└── linker/                    # 链接脚本
    └── STM32F103XX_FLASH.ld
```

### 寄存器头文件获取

最干净的方式是从 **STM32CubeF1** 固件包中提取 CMSIS 部分：

```bash
# 克隆官方固件包（以F1为例，其他系列类似）
git clone https://github.com/STMicroelectronics/STM32CubeF1.git

# 你只需要这些文件：
# STM32CubeF1/Drivers/CMSIS/Device/ST/STM32F1xx/Include/
#   ├── stm32f1xx.h
#   ├── stm32f103xb.h        <-- 寄存器结构体定义（最关键）
#   └── system_stm32f1xx.h
# STM32CubeF1/Drivers/CMSIS/Include/
#   ├── core_cm3.h
#   └── cmsis_gcc.h
```



### 启动文件 & 链接脚本





┌─────────────────────────────────────────────────┐
│           最主流的寄存器开发组合                    │
├─────────────────────────────────────────────────┤
│                                                 │
│   编辑器:    VS Code + Cortex-Debug 插件         │
│   编译器:    arm-none-eabi-gcc                   │
│   构建:      Makefile                            │
│   启动文件:  从 STM32CubeMX 生成的 .s 文件       │
│   链接脚本:  从 STM32CubeMX 生成的 .ld 文件       │
│   寄存器定义: CMSIS 头文件（stm32f103xb.h）       │
│   烧录:      OpenOCD / st-flash                  │
│   调试:      OpenOCD + GDB (+ SVD 寄存器视图)     │
│                                                 │
│   关键原则: 不引入 HAL/LL 库，直接读写寄存器       │
└─────────────────────────────────────────────────┘
```

