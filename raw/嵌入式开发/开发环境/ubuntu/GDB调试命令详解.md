---
title: "GDB调试命令详解"
category: "STM32/开发环境"
tags: [GDB, 调试命令, 断点, 观察点, 寄存器]
abstract: "GDB调试命令完整手册，涵盖连接控制、断点、数据查看、修改等所有常用命令"
source: "原创"
update_time: 2026-05-28
status: 完成
type: 资料摘抄
---

## 一句话定义

GDB是GNU调试器，支持断点设置、单步执行、寄存器查看、内存修改等功能，是嵌入式开发的核心调试工具。

## 核心内容

> **前置条件**  
> 你已经按照前面的指南生成了 `firmware.elf`，并且 OpenOCD 已在后台运行并监听 `3333` 端口。  
> 在终端启动 GDB：
> 
> ```bash
> arm-none-eabi-gdb firmware.elf
> ```

### 1. GDB 核心概念与基础操作

#### 1.1 启动与连接

```gdb
# 连接远程调试服务器（OpenOCD）
(gdb) target remote localhost:3333
# 暂停目标 CPU
(gdb) monitor reset halt
# 下载程序到 Flash
(gdb) load
# 复位并准备从复位向量运行
(gdb) monitor reset init
```

**`monitor` 命令** 用于向远程服务器（OpenOCD）直接发送指令，如：

```gdb
(gdb) monitor reset          # 仅复位
(gdb) monitor halt           # 暂停 CPU
(gdb) monitor reg            # 显示核心寄存器（从 OpenOCD 侧看）
```

#### 1.2 退出 GDB

```gdb
(gdb) quit
```

若目标仍在运行，GDB 会提示确认，或可先 `detach` 再退出：

```gdb
(gdb) detach
(gdb) quit
```

### 2. 执行控制命令

#### 2.1 运行与暂停

|命令|缩写|功能|
|---|---|---|
|`continue`|`c`|继续运行直到下一个断点/观察点|
|`step`|`s`|单步执行（进入函数）|
|`next`|`n`|单步执行（跳过函数）|
|`stepi`|`si`|单步汇编指令（进入）|
|`nexti`|`ni`|单步汇编指令（跳过）|
|`finish`|`fin`|执行完当前函数并返回|
|`until`|`u`|执行到当前循环结束或指定行|
|`Ctrl+C`||手动暂停运行中的程序|

**示例：**

```gdb
(gdb) continue
# 按 Ctrl+C 手动暂停
(gdb) next
(gdb) step
(gdb) finish
```

如果想知道 LED 点亮前后程序执行到了哪里：

```gdb
(gdb) break main
(gdb) continue       # 停在 main 入口
(gdb) next           # 执行一条 C 语句，比如 RCC_APB2ENR |= ...
(gdb) step           # 若调用了函数则进入
```

#### 2.2 信号与异常处理

当 HardFault 等异常发生时，GDB 会自动停止。可以使用：

```gdb
(gdb) info signals          # 查看所有信号及当前处理方式
(gdb) handle SIGINT stop    # 设置收到 SIGINT 时暂停
```

### 3. 断点（Breakpoints）

#### 3.1 设置断点

```gdb
break 函数名
break 文件名:行号
break *地址
```

**示例：**

```gdb
(gdb) break main
(gdb) break main.c:18
(gdb) break *0x08000100
```

#### 3.2 条件断点

```gdb
break 位置 if 条件
```

**示例：** 当变量 `counter == 10` 时才停在某行

```gdb
(gdb) break main.c:22 if counter == 10
```

#### 3.3 临时断点（只停一次）

```gdb
tbreak 位置
```

#### 3.4 管理断点

```gdb
(gdb) info breakpoints      # 查看所有断点和观察点
(gdb) enable 1               # 启用 1 号断点
(gdb) disable 2              # 禁用 2 号断点
(gdb) delete 3               # 删除 3 号断点
(gdb) delete                 # 删除所有断点
```

#### 3.5 硬件与软件断点

Cortex-M 通常有 6 个硬件断点。GDB 默认优先使用硬件断点，如果不够会自动切换为软件断点（修改 Flash）。可强制指定：

```gdb
(gdb) hbreak *0x08000100     # 强制硬件断点
```

查看硬件断点占用（通过 OpenOCD）：

```gdb
(gdb) monitor bp             # 列出硬件断点
```

### 4. 观察点（Watchpoints） – 监测数据变化

观察点是寄存器级调试的灵魂，它们由 DWT 硬件提供，数量一般 4 个。

#### 4.1 设置观察点

```gdb
watch 表达式         # 写观察点
rwatch 表达式        # 读观察点
awatch 表达式        # 读写观察点
```

**示例：** 监测 GPIOC ODR 寄存器的写入

```gdb
(gdb) watch *(unsigned int*)0x4001100C
# 或者先定义变量
(gdb) set $odr = (unsigned int*)0x4001100C
(gdb) watch *$odr
```

当任何指令修改 ODR 时，GDB 会立即停下并显示：

```
Hardware watchpoint 2: *(unsigned int *) 0x4001100c
Old value = 0
New value = 8192          # 即 bit13 置1
```

**条件观察点：**

```gdb
(gdb) watch *$odr if (*$odr & 0x2000) != 0
```

#### 4.2 管理观察点

```gdb
(gdb) info watchpoints     # 查看所有观察点
(gdb) delete 2             # 删除编号2的观察点
```

### 5. 数据与寄存器查看

#### 5.1 查看 CPU 核心寄存器

```gdb
(gdb) info registers       # 所有通用寄存器
(gdb) print/x $pc          # 程序计数器
(gdb) print/x $sp          # 栈指针
(gdb) print/x $lr          # 链接寄存器
(gdb) print/x $psr         # 程序状态寄存器
```

#### 5.2 查看内存/外设寄存器（`x` 命令）

```gdb
x /NFS 地址
```

- `N`：重复次数
- `F`：格式 `x`(十六进制) `d`(十进制) `t`(二进制) `c`(字符)
- `S`：大小 `b`(字节) `h`(半字) `w`(字) `g`(8字节)

**示例：**

```gdb
# 读取 GPIOC_ODR (地址 0x4001100C)
(gdb) x /xw 0x4001100C
0x4001100c: 0x00000000
# 连续查看 4 个字，从 RCC_APB2ENR 开始
(gdb) x /4xw 0x40021018
# 以二进制显示一个字
(gdb) x /tw 0x40011004
# 显示半字
(gdb) x /xh 0x20000000
```

#### 5.3 格式化打印变量或表达式

```gdb
(gdb) print 表达式
(gdb) print /x 表达式     # 十六进制
(gdb) print /t 表达式     # 二进制
```

**示例：** 打印指针指向的值

```gdb
(gdb) set $pGPIOC_ODR = (unsigned int*)0x4001100C
(gdb) print *$pGPIOC_ODR
$1 = 0
(gdb) print /x *$pGPIOC_ODR
```

#### 5.4 显示局部/全局变量

```gdb
(gdb) info locals        # 当前函数的局部变量
(gdb) info args          # 当前函数的参数
(gdb) print 变量名
```

对于纯寄存器程序，变量极少，主要靠 `x` 和 `$` 定义快捷变量。

#### 5.5 查看 CPU 模式与状态

```gdb
(gdb) show language
(gdb) info threads            # RTOS 调试时有用
(gdb) info frame               # 当前栈帧信息
```

### 6. 栈与调用跟踪

#### 6.1 查看调用栈

```gdb
(gdb) backtrace       # 或 bt
(gdb) bt full         # 显示完整栈帧，包含局部变量
```

#### 6.2 切换栈帧

```gdb
(gdb) frame 0
(gdb) frame 1
(gdb) up
(gdb) down
```

#### 6.3 查看栈内容

```gdb
(gdb) info frame
Stack level 0, frame at 0x20000f00:
 pc = 0x08000120 in main (main.c:18); saved pc 0x08000100
```

### 7. 修改程序状态

#### 7.1 修改变量或内存

```gdb
(gdb) set 变量 = 值
(gdb) set {类型}地址 = 值
```

**示例：** 手动翻转 LED

```gdb
(gdb) set *(unsigned int*)0x4001100C = 0x2000    # LED 灭
(gdb) set *(unsigned int*)0x4001100C = 0x0000    # LED 亮
```

修改 CPU 寄存器：

```gdb
(gdb) set $r0 = 0x55
(gdb) set $pc = 0x08000100       # 改变程序流向（需谨慎）
```

#### 7.2 跳过某条指令

临时修改 PC 跳过当前指令：

```gdb
(gdb) set $pc = $pc + 4         # 跳过一条 32 位指令
```

#### 7.3 返回指定值（跳过函数执行）

```gdb
(gdb) return 表达式
```

### 8. 反汇编与汇编级调试

#### 8.1 反汇编

```gdb
(gdb) disassemble main          # 反汇编整个函数
(gdb) disassemble /m main       # 混合源码和汇编
(gdb) disassemble /r main       # 显示机器码
(gdb) disassemble 0x08000100,0x08000120  # 指定地址范围
```

#### 8.2 查看当前指令

```gdb
(gdb) x /i $pc                  # 显示 PC 指向的汇编指令
(gdb) display /i $pc            # 每次暂停自动显示下一条指令
```

#### 8.3 指令级单步

如前所述 `stepi` / `nexti`。

### 9. 便捷变量与自定义命令

#### 9.1 定义 GDB 变量

```gdb
(gdb) set $RCC_APB2ENR = (unsigned int*)0x40021018
(gdb) x /xw $RCC_APB2ENR
```

这些变量在会话中一直存在，可以重复使用。

#### 9.2 定义宏/命令组合

使用 `define` 创建自定义命令，比如一次复位并重新加载：

```gdb
(gdb) define reload
Type commands for definition of "reload".
End with a line saying just "end".
>monitor reset halt
>load
>monitor reset init
>end
(gdb) reload
```

#### 9.3 记录命令序列到日志

```gdb
(gdb) set logging on           # 日志输出到 gdb.txt
(gdb) set logging off
```

### 10. 符号文件与源码管理

- `file firmware.elf` – 加载符号文件
- `list` – 显示源码
- `list 行号` 或 `list 函数名`
- `directory 路径` – 添加源码搜索目录
- `info sources` – 列出所有源文件

**示例：**

```gdb
(gdb) list main
(gdb) list 22
(gdb) directory ../src
```

### 11. 脚本与批量执行

#### 11.1 启动时执行脚本

```bash
arm-none-eabi-gdb -x script.gdb firmware.elf
```

`script.gdb` 内容示例：

```
target remote localhost:3333
monitor reset halt
load
break main
continue
```

#### 11.2 在 GDB 内执行脚本

```gdb
(gdb) source my_commands.gdb
```

### 12. 图形化视图（TUI 模式）

GDB 自带文本界面，适合快速查看源码和汇编。

|命令|功能|
|---|---|
|`layout src`|仅源码|
|`layout asm`|仅汇编|
|`layout split`|源码+汇编|
|`layout regs`|寄存器窗口|
|`focus cmd/src/asm`|切换焦点|
|`refresh`|刷新屏幕|
|`Ctrl+X, A`|退出 TUI|
|`tui enable` / `tui disable`|启用/禁用 TUI|

**示例：**

```gdb
(gdb) layout split
(gdb) layout regs
(gdb) refresh
```

### 13. 常见调试场景实战

#### 场景 1：确认时钟是否使能

```gdb
(gdb) x /xw 0x40021018          # RCC_APB2ENR
# 检查 bit4 是否为 1
(gdb) print /t (*(unsigned int*)0x40021018)
```

#### 场景 2：监测 GPIO 输出翻转

```gdb
(gdb) watch *(unsigned int*)0x4001100C
(gdb) continue
# 程序每次修改 ODR 都会停下，显示新旧值
```

#### 场景 3：追踪 HardFault 原因

发生 HardFault 后：

```gdb
(gdb) bt full                # 查看栈跟踪
(gdb) frame 0
(gdb) print/x $pc            # 发生异常时的指令地址
(gdb) disassemble $pc-8,$pc+8
(gdb) print/x $lr            # EXC_RETURN，判断是从线程还是 Handler 进入
```

进一步分析栈帧可找到出错前的寄存器状态。

#### 场景 4：快速测试修改

```gdb
(gdb) break main.c:20
(gdb) continue
# 停在 LED 点亮之后
(gdb) set *(unsigned int*)0x4001100C = 0x2000    # 立即关灯
(gdb) continue
```

### 14. 常用命令速查表

|目的|命令|
|---|---|
|连接目标|`target remote localhost:3333`|
|暂停|`Ctrl+C` 或 `monitor halt`|
|继续|`continue`|
|单步（源码）|`step` / `next`|
|单步（指令）|`stepi` / `nexti`|
|设置断点|`break 位置`|
|条件断点|`break 位置 if 条件`|
|观察点|`watch 表达式`|
|查看所有断点/观察点|`info breakpoints`|
|删除断点|`delete 编号`|
|查看寄存器|`info registers` / `print $r0`|
|查看内存|`x /格式 地址`|
|修改变量/内存|`set 变量=值`|
|调用栈|`backtrace`|
|反汇编|`disassemble`|
|源码列表|`list`|
|TUI 模式|`layout split` / `Ctrl+X A`|
|下载程序|`load`|
|复位|`monitor reset init`|
|帮助|`help 命令名`|

掌握这些命令，你就能在 Ubuntu 下对 STM32 进行**寄存器级别的精密调试**。每个命令都可以立即在之前编译的 LED 项目中尝试，配合实验加深理解。

## 注意事项 & 踩坑

- 硬件断点数量有限（Cortex-M3通常6个），用完需要删除才能新建
- 观察点由DWT硬件提供，通常只有4个
- 修改PC寄存器要谨慎，可能导致程序跑飞
- TUI模式下退出用 `Ctrl+X, A`

## 相关笔记

- [[STM32寄存器级调试实战]]
- [[STM32调试指南]]
- [[Ubuntu 24.04调试器配置]]

## 参考来源

- GDB 官方手册：https://sourceware.org/gdb/documentation/
- ARM Cortex-M3 技术手册
