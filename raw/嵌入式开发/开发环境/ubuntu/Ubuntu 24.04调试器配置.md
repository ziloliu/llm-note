---
title: "Ubuntu 24.04调试器配置"
category: "STM32/开发环境"
tags: [调试器, gdb-multiarch, Ubuntu, VS Code]
abstract: "Ubuntu 24.04中使用gdb-multiarch替代arm-none-eabi-gdb的配置方法"
source: "原创"
update_time: 2026-05-28
status: 完成
type: 实操
---

## 一句话定义

Ubuntu 24.04开始，`arm-none-eabi-gdb`已被替换为通用的`gdb-multiarch`，功能完全相同，可直接使用。

## 核心内容

### 背景说明

Ubuntu 从 24.04 开始，已将 `arm-none-eabi-gdb` 替换成了通用的多架构调试器 `gdb-multiarch`。

所以 `apt` 给出的 `gdb-multiarch` 就是你要的调试器，直接用它就行，不需要再找 `arm-none-eabi-gdb` 这条单独的命令。

### 直接使用 `gdb-multiarch`

你现在就可以用 `gdb-multiarch` 来调试 STM32：

```bash
gdb-multiarch your_firmware.elf
```

连接调试器（如 OpenOCD、J-Link、ST-Link）后，在 GDB 内执行：

```gdb
target extended-remote :3333   # 根据你实际端口修改
load
monitor reset init
continue
```

**它完全支持 ARM Cortex-M，功能与专用 `arm-none-eabi-gdb` 没有区别。**

### 在 VS Code 中配置

如果你在 VS Code 里使用 Cortex-Debug 插件，只需在 `launch.json` 中把 `miDebuggerPath` 改成 `gdb-multiarch`：

```json
{
    "name": "Cortex Debug",
    "type": "cortex-debug",
    "request": "launch",
    "servertype": "openocd",
    "cwd": "${workspaceRoot}",
    "executable": "./build/your_firmware.elf",
    "configFiles": [
        "interface/stlink.cfg",
        "target/stm32f1x.cfg"
    ],
    "gdbPath": "gdb-multiarch",   // 原来是 "arm-none-eabi-gdb"
    "device": "STM32F103C8",
    "svdFile": "..."
}
```

### 如果一定要 `arm-none-eabi-gdb` 命令

有些工具或脚本可能硬编码了这个命令名，那就从 ARM 官方下载完整工具链手动安装：

1. **下载 ARM GNU Toolchain**：  
   [https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads)  
   选择 **AArch32 bare-metal target (arm-none-eabi)** 的 Linux x86_64 Tarball。

2. **解压并配置环境**：
   ```bash
   sudo mkdir -p /opt/toolchains
   sudo tar -xf gcc-arm-none-eabi-*-linux.tar.bz2 -C /opt/toolchains/
   echo 'export PATH=$PATH:/opt/toolchains/gcc-arm-none-eabi-*/bin' >> ~/.bashrc
   source ~/.bashrc
   ```

3. **验证**：
   ```bash
   arm-none-eabi-gdb --version
   ```

这个方法装出来的就是带 `arm-none-eabi-gdb` 的完整工具链，和 `arm-none-eabi-gcc` 一起放在 `bin` 目录下。

## 注意事项 & 踩坑

- Ubuntu 24.04 默认只提供 `gdb-multiarch`，不再有 `arm-none-eabi-gdb` 包
- `gdb-multiarch` 功能与 `arm-none-eabi-gdb` 完全相同，无需担心兼容性
- VS Code Cortex-Debug 插件需要修改 `gdbPath` 配置

## 相关笔记

- [[STM32调试指南]]
- [[ARM工具链安装与配置]]

## 参考来源

- Ubuntu 24.04 发行说明
- ARM GNU Toolchain 官方下载
