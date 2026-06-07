---
title: "STM32寄存器级调试实战"
category: "STM32/开发环境"
tags: [调试, 寄存器, OpenOCD, GDB, 观察点]
abstract: "STM32寄存器级调试的完整流程，包括硬件连接、OpenOCD启动、GDB调试技巧"
source: "原创"
update_time: 2026-05-28
status: 完成
type: 实操
---

## 一句话定义

STM32寄存器级调试通过OpenOCD连接硬件，使用GDB查看和修改CPU寄存器、外设寄存器，实现底层硬件调试。

## 核心内容

### 1. 启动调试环境

#### 1.1 连接硬件

- 将 ST-Link（或 J-Link、DAP-Link）连接到 STM32 开发板
- 使用 `lsusb` 检查调试器是否被识别，例如会看到 `STMicroelectronics ST-LINK/V2`

#### 1.2 启动 OpenOCD（作为 GDB 服务器）

**对于 ST-Link V2 和 STM32F1：**

```bash
openocd -f interface/stlink.cfg -f target/stm32f1x.cfg
```

若使用 J-Link：

```bash
openocd -f interface/jlink.cfg -f target/stm32f1x.cfg
```

成功启动后会看到：

```
Info : Listening on port 3333 for gdb connections
Info : Listening on port 6666 for tcl connections
Info : Listening on port 4444 for telnet connections
```

保持此终端运行。

#### 1.3 启动 GDB 并连接

打开另一个终端：

```bash
arm-none-eabi-gdb firmware.elf
```

在 GDB 中输入：

```gdb
(gdb) target remote localhost:3333
```

连接成功后，执行：

```gdb
(gdb) monitor reset halt      # 复位芯片并暂停
(gdb) load                    # 将固件下载到 Flash
(gdb) monitor reset init      # 再次复位，使程序从复位向量开始
```

### 2. 寄存器级调试核心命令

#### 2.1 查看 CPU 内核寄存器

```gdb
(gdb) info registers
```

可看到 `r0`-`r15`、`sp`、`lr`、`pc`、`xPSR` 等。

单独查看某个寄存器：

```gdb
(gdb) print/x $pc
(gdb) print/x $sp
```

#### 2.2 查看外设寄存器（内存映射 I/O）

所有外设寄存器都是内存地址，使用 `x`（examine）命令读取：

```gdb
# 读取 GPIOC 的 CRH 寄存器（地址 0x40011004）
(gdb) x /xw 0x40011004
# 输出举例：0x40011004: 0x00300000   （可见 MODE13=11b）
```

格式说明：
- `x`：查看内存
- `/xw`：十六进制（x）四字节（w）
- 其他格式：`/xh`（半字）、`/xb`（字节）、`/d`（十进制）、`/t`（二进制）

**连续查看多个地址：**

```gdb
# 查看 RCC_APB2ENR、GPIOC_CRH、GPIOC_ODR 三个寄存器
(gdb) x /3xw 0x40021018
```

#### 2.3 使用 GDB 变量保存外设地址

为避免重复输入长地址，可以定义便捷变量：

```gdb
(gdb) set $RCC_APB2ENR = (unsigned int*)0x40021018
(gdb) set $GPIOC_ODR   = (unsigned int*)0x4001100C
(gdb) x /xw $RCC_APB2ENR
(gdb) x /xw $GPIOC_ODR
```

#### 2.4 观察点（Watchpoint）—— 监测寄存器变化

**硬件观察点**（推荐，不占用 CPU 资源，但数量有限，通常 4-6 个）：

```gdb
# 当 GPIOC ODR 被写入时自动停止
(gdb) watch *(unsigned int*)0x4001100C
(gdb) continue
```

当程序修改 ODR 时，GDB 会停下并显示旧值和新值。

**读观察点**（监测读取操作）：

```gdb
(gdb) rwatch *(unsigned int*)0x4001100C
```

**访问观察点**（读或写均触发）：

```gdb
(gdb) awatch *(unsigned int*)0x4001100C
```

**条件观察点**：

```gdb
(gdb) watch *(unsigned int*)0x4001100C if (*(unsigned int*)0x4001100C & 0x2000) != 0
```

查看已设置的观察点：

```gdb
(gdb) info watchpoints
```

删除：

```gdb
(gdb) delete <编号>
```

#### 2.5 断点与条件断点

```gdb
(gdb) break main                  # 在 main 入口
(gdb) break main.c:15             # 在 main.c 第 15 行
(gdb) break *0x08000100           # 在指定地址
```

**条件断点**：

```gdb
(gdb) break main.c:18 if counter == 5
```

**临时断点**（只停一次）：

```gdb
(gdb) tbreak main.c:25
```

查看断点：

```gdb
(gdb) info breakpoints
```

#### 2.6 单步执行与汇编级调试

```gdb
(gdb) step          # 进入函数（源码级）
(gdb) next          # 越过函数（源码级）
(gdb) stepi         # 执行一条汇编指令（进入）
(gdb) nexti         # 执行一条汇编指令（越过）
```

**查看当前代码与汇编对照：**

```gdb
(gdb) layout split       # 上半部分源码，下半部分汇编
(gdb) layout asm         # 仅汇编
```

退出窗口用 `Ctrl+X, A`。

**反汇编：**

```gdb
(gdb) disassemble /m main
```

#### 2.7 手动修改寄存器和内存

**修改 CPU 内核寄存器：**

```gdb
(gdb) set $r0 = 0x55
(gdb) set $pc = 0x08000100
```

**修改外设寄存器/内存（如翻转 LED）：**

```gdb
# 将 GPIOC ODR 的 bit13 写 1（LED 灭）
(gdb) set {int}0x4001100C = 0x2000
# 或将 bit13 清 0（LED 亮）
(gdb) set {int}0x4001100C = 0x0000
# 也可以按位操作
(gdb) set *(unsigned int*)0x4001100C |= (1<<13)
```

#### 2.8 查看处理器模式和状态

```gdb
(gdb) print/x $psr             # 程序状态寄存器
(gdb) print $cpsr              # 如果架构支持
```

（Cortex-M 中，xPSR 是组合寄存器）

#### 2.9 直接使用 OpenOCD telnet 调试

另开终端，连接 OpenOCD 的 4444 端口：

```bash
telnet localhost 4444
```

在 OpenOCD 控制台中执行：

```
> halt                         # 暂停 CPU
> reg                          # 显示内核寄存器
> mdw 0x40011004               # 读取内存双字（32位）
> mww 0x4001100C 0x00002000    # 写入双字，灭 LED
> resume                       # 恢复运行
> reset halt                   # 复位并暂停
```

常用命令：
- `mdw <addr> [count]` – 读双字
- `mww <addr> <value>` – 写双字
- `mdh` / `mwh` – 半字
- `mdb` / `mwb` – 字节
- `flash erase_sector 0 0 0` – 擦除 Flash（参数：bank first last）

### 3. 进阶：硬件断点与 DWT 资源

Cortex-M3/M4 通常有 6 个硬件断点（FPB）和 4 个观察点（DWT）。GDB 会自动使用硬件资源，当设置普通断点时优先使用硬件断点，数量不够会转为软件断点（改 Flash）。

查看已使用的硬件断点：

```gdb
(gdb) monitor bp                 # 在 OpenOCD telnet 中查看
```

### 4. 常见问题与解决

|问题|可能原因|解决方法|
|---|---|---|
|`Error: init mode failed`|连接问题或配置错误|检查接线，按住复位键再上电，尝试在 `openocd` 命令后加 `-c "reset_config srst_only srst_nogate"`|
|GDB 无法连接 `localhost:3333`|OpenOCD 未启动或端口占用|确认 OpenOCD 正在运行，`netstat -tlnp \| grep 3333`|
|程序下载后不运行|未执行 `monitor reset init` 或时钟未配置|执行 `monitor reset init`；检查程序本身|
|无法设置观察点|数量已满|删除不用的 watchpoint，或使用 `awatch` 替代软件仿真|
|`load` 失败|Flash 被保护|在 OpenOCD 控制台执行 `flash erase_sector 0 0 0`，或解除写保护|

### 5. 使用 VS Code 图形化调试（可选）

若想将寄存器查看、断点等集成到图形界面，推荐使用 Cortex-Debug 插件。

**安装插件：**  
在 VS Code 扩展市场搜索并安装 `Cortex-Debug`（由 marus25 提供）。

**配置 `.vscode/launch.json`：**

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "STM32 Debug",
            "cwd": "${workspaceRoot}",
            "executable": "./firmware.elf",
            "request": "launch",
            "type": "cortex-debug",
            "servertype": "openocd",
            "configFiles": [
                "interface/stlink.cfg",
                "target/stm32f1x.cfg"
            ],
            "svdFile": "STM32F103.svd"   // 可从 ST 官网下载 SVD 文件，使外设寄存器可视化
        }
    ]
}
```

启动调试后，左侧 "Cortex Registers" 面板可直接看到外设寄存器，无需手动输入地址。

## 注意事项 & 踩坑

- 硬件观察点数量有限（通常4-6个），用完需要删除才能新建
- 修改PC寄存器要谨慎，可能导致程序跑飞
- OpenOCD必须保持运行，关闭后GDB会断开连接

## 相关笔记

- [[STM32调试指南]]
- [[GDB调试命令详解]]
- [[Ubuntu 24.04调试器配置]]

## 参考来源

- OpenOCD 官方文档
- GDB 官方手册
- Cortex-M3 技术手册
