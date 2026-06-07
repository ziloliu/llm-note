---
title: "Windows下STM32寄存器开发启动文件配置"
category: "STM32/开发环境"
tags: [Windows, STM32, 寄存器开发, 启动文件, 标准库]
abstract: "Windows下STM32寄存器开发所需的启动文件配置与标准库文件准备"
source: "原创"
update_time: 2026-05-25
status: 完成
type: 实操
---

## 一句话定义

Windows下进行STM32寄存器开发需要从标准库获取启动文件、链接脚本和CMSIS文件，并正确组织项目结构。

## 核心内容

### 标准库文件下载

标准库文件下载网页：https://www.st.com.cn/zh/embedded-software/stm32-standard-peripheral-libraries/products.html

- 选择 **STSW-STM32048**
- 适配 STM32F1xxx 系列

### 所需文件清单

| 文件 | 路径 | 说明 |
|------|------|------|
| core_cm3.c | Libraries/CMSIS/CM3/CoreSupport/ | ARM内核支持文件 |
| core_cm3.h | Libraries/CMSIS/CM3/CoreSupport/ | ARM内核头文件 |
| startup_stm32f10x_hd.s | Libraries/CMSIS/CM3/DeviceSupport/ST/STM32F10x/startup/arm/ | 启动文件（HD大容量型） |
| system_stm32f10x.h | Libraries/CMSIS/CM3/DeviceSupport/ST/STM32F10x/ | 系统配置文件 |
| system_stm32f10x.c | Libraries/CMSIS/CM3/DeviceSupport/ST/STM32F10x/ | 系统实现文件 |
| stm32f10x.h | Libraries/CMSIS/CM3/DeviceSupport/ST/STM32F10x/ | 外设寄存器定义 |

![](01_stm32-startup-files.png)

### 启动文件选型说明

| 型号后缀 | 说明 |
|----------|------|
| `_hd` | High Density，大容量型（Flash ≥ 256KB） |
| `_md` | Medium Density，中容量型（Flash 64-256KB） |
| `_ld` | Low Density，小容量型（Flash 32-64KB） |

根据实际芯片型号选择对应的启动文件。例如 STM32F103ZE 选择 `_hd`，STM32F103C8T6 选择 `_md`。

### 项目文件组织

建议的目录结构：

```
Project/
├── Libraries/
│   └── CMSIS/
│       ├── CoreSupport/
│       │   ├── core_cm3.c
│       │   └── core_cm3.h
│       └── DeviceSupport/
│           └── ST/
│               └── STM32F10x/
│                   ├── system_stm32f10x.c
│                   ├── system_stm32f10x.h
│                   ├── stm32f10x.h
│                   └── startup/
│                       └── startup_stm32f10x_hd.s
└── User/
    ├── main.c
    ├── stm32f10x_it.c
    └── stm32f10x_it.h
```

### 注意事项 & 踩坑

1. **启动文件选型错误**：必须根据芯片型号选择正确的启动文件，否则程序无法运行
2. **链接脚本配置**：除了启动文件，还需要对应的 `.ld` 链接脚本定义Flash和RAM地址
3. **标准库版本**：建议使用 STM32F10x_StdPeriph_Lib_V3.6.0 版本

## 参考来源

- ST 官方标准库 STM32F10x_StdPeriph_Lib_V3.6.0
