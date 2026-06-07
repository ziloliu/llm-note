---
title: "STM32调试指南"
category: "STM32/开发环境"
tags: [调试, GDB, OpenOCD, VS Code, Cortex-Debug]
abstract: "详解STM32嵌入式调试的完整流程，包括命令行GDB和VS Code图形化调试"
source: "原创"
update_time: 2026-05-28
status: 完成
type: 实操
---

## 一句话定义

STM32调试通过SWD接口连接ST-Link调试器，使用OpenOCD作为GDB Server，配合GDB或VS Code Cortex-Debug插件实现断点、单步、寄存器查看等功能。

## 核心内容

### 调试的整体架构

```
你的电脑                                    STM32 芯片
┌───────────────────────────────────┐      ┌──────────────────┐
│                                   │      │                  │
│  GDB（调试器客户端）                │      │  CPU 执行你的代码 │
│  arm-none-eabi-gdb                │      │                  │
│       │                           │      │  内置调试硬件：    │
│       │  TCP :3333                │      │  ├── 断点寄存器   │
│       ▼                           │      │  ├── 观察点寄存器  │
│  OpenOCD（GDB Server）            │      │  └── DWT 周期计数器│
│       │                           │      │                  │
│       │  USB                      │      │                  │
│       ▼                           │      │                  │
│  ST-Link（调试器硬件）  ══SWD═══════════════SWD接口           │
│  SWDIO + SWDCK                    │      │                  │
└───────────────────────────────────┘      └──────────────────┘
```

**调试的原理：**

芯片内部有一套调试硬件（CoreSight），通过 SWD 两根线对外通信
ST-Link 把 USB 协议转成 SWD 协议
OpenOCD 把 GDB 的调试命令翻译成 SWD 操作
GDB 给你提供人机交互界面

你输入 "在 main 函数打断点"
  → GDB 发送 "插入断点" 命令
  → OpenOCD 转成 SWD 数据包
  → ST-Link 通过 SWD 线发给芯片
  → 芯片的断点寄存器记录这个地址
  → CPU 执行到这个地址时自动暂停
  → 暂停后你可以查看寄存器、内存、变量

### 第一步：确保工具安装好

```bash
# 检查 GDB
arm-none-eabi-gdb --version

# 检查 OpenOCD
openocd --version

# 没装的话
sudo apt install gdb-multiarch openocd
# 或者
sudo apt install gcc-arm-none-eabi   # 这个包里包含 arm-none-eabi-gdb
```

### 第二步：Makefile 中加 debug 目标

```makefile
# 确保编译时用 -O0 和 -g（调试时不用优化）
# 在 Makefile 头部临时改：
CFLAGS = $(MCU) -D$(DEVICE) $(INCLUDES) \
         -Wall -fdata-sections -ffunction-sections \
         -g -O0
#                  ^^^^
#                  -g   生成调试信息（符号表、行号映射）
#                  -O0  关闭优化（调试时变量值不会被优化掉）

# debug 目标
debug: $(ELF)
	openocd -f interface/stlink.cfg -f target/stm32f1x.cfg &
	sleep 1
	$(PREFIX)gdb $(ELF) \
	    -ex "target remote localhost:3333" \
	    -ex "monitor reset halt" \
	    -ex "break main" \
	    -ex "continue"
```

### 第三步：命令行 GDB 调试（基础）

```bash
# 终端1：启动 OpenOCD（保持运行）
openocd -f interface/stlink.cfg -f target/stm32f1x.cfg
```

```bash
# 终端2：启动 GDB
arm-none-eabi-gdb build/firmware.elf
```

#### 连接芯片

```gdb
(gdb) target remote localhost:3333
# 连接到 OpenOCD 的 GDB Server
# 输出：Remote debugging using localhost:3333

(gdb) monitor reset halt
# monitor → 把命令发给 OpenOCD 执行
# reset halt → 复位芯片并暂停在第一条指令
# 输出：target halted due to debug-request, current mode: Thread
#       xPSR: 0x01000000 pc: 0x08000100
```

#### 打断点

```gdb
(gdb) break main
# 在 main 函数入口打断点
# 输出：Breakpoint 1 at 0x8000140: file src/main.c, line 7.

(gdb) break src/main.c:12
# 在 main.c 第 12 行打断点
# 输出：Breakpoint 2 at 0x8000158: file src/main.c, line 12.

(gdb) break gpio_init
# 在 gpio_init 函数入口打断点

(gdb) info break
# 查看所有断点
# Num  Type      Disp  Enb  Address    What
# 1    breakpoint  keep  y   0x08000140 in main at src/main.c:7
# 2    breakpoint  keep  y   0x08000158 in src/main.c:12
```

#### 运行和暂停

```gdb
(gdb) continue
# 继续运行，直到碰到断点
# 输出：Continuing.
#       Breakpoint 1, main () at src/main.c:7

(gdb) continue
# 再次 continue，到下一个断点
```

#### 单步执行

```gdb
(gdb) next
# 执行一行 C 代码，不进入函数内部
# 等价于 VS Code 的 "Step Over"

(gdb) step
# 执行一行 C 代码，进入函数内部
# 等价于 VS Code 的 "Step Into"

(gdb) finish
# 执行到当前函数返回
# 等价于 VS Code 的 "Step Out"

(gdb) nexti
# 执行一条汇编指令（不是一行 C）

(gdb) stepi
# 执行一条汇编指令，如果是指令跳转就跳进去
```

#### 查看变量和内存

```gdb
(gdb) print my_variable
# 打印变量值
# $1 = 42

(gdb) print /x my_variable
# 以十六进制打印
# $1 = 0x2a

(gdb) print /t my_variable
# 以二进制打印
# $1 = 0b00101010

(gdb) print GPIOA->ODR
# 直接读取外设寄存器
# $2 = 0x00000020

(gdb) print RCC->APB2ENR
# $3 = 0x00000014

(gdb) display my_variable
# 每次暂停时自动显示这个变量

(gdb) watch my_variable
# 观察点：当这个变量的值改变时自动暂停
# 硬件观察点，STM32 支持 4 个

(gdb) info locals
# 显示当前函数所有局部变量

(gdb) info registers
# 显示 CPU 寄存器
# r0  = 0x00000000    r1  = 0x40010800
# r2  = 0x33333333    r3  = 0x00000000
# ...
# pc  = 0x08000150    lr  = 0x0800014b
# sp  = 0x20004ff0

(gdb) x/16x 0x40010800
# 查看内存，从 GPIOA 基地址开始的 16 个字（4字节）
# 0x40010800: 0x33333333  0x00000000  0x00000000  0x00000020
# 0x40010810: 0x00000000  0x00000000  0x00000000  0x00000000
#              ^^^^^^^^^
#              GPIOA->CRL = 0x33333333（PA5推挽输出50MHz）

(gdb) x/4x &my_array
# 查看数组内容
```

**x 命令格式：x/数量格式单位 地址**

```
数量：显示多少个
格式：x=十六进制, d=十进制, t=二进制, c=字符, s=字符串
单位：b=字节, h=半字(2字节), w=字(4字节), g=巨字(8字节)

x/16xb 0x20000000  → 从 RAM 起始开始看 16 个字节
x/4xw  0x40010800  → 从 GPIOA 开始看 4 个 32 位寄存器
x/1i   $pc         → 查看当前 PC 指向的那条指令
x/10i  $pc         → 查看从当前 PC 开始的 10 条指令（反汇编）
```

#### 查看调用栈

```gdb
(gdb) backtrace
# 显示函数调用链
# #0  delay (n=325407) at src/main.c:14
# #1  0x08000160 in main () at src/main.c:20

(gdb) frame 1
# 切换到第 1 帧（main 函数的上下文）
# 现在可以查看 main 函数里的变量

(gdb) info args
# 显示当前函数的参数
```

#### 修改变量和寄存器

```gdb
(gdb) set my_variable = 100
# 在运行时修改变量值

(gdb) set GPIOA->ODR = 0x00000000
# 直接写外设寄存器（关 LED）

(gdb) set GPIOA->ODR = 0x00000020
# 写寄存器（开 LED，PA5 = bit5）

(gdb) set $pc = 0x08000140
# 修改 PC 寄存器，跳到指定地址执行（慎用）
```

### 完整调试会话演示

```bash
# 终端1：启动 OpenOCD
$ openocd -f interface/stlink.cfg -f target/stm32f1x.cfg

# 输出：
# Info : clock speed 1000 kHz
# Info : STLINK V2J37S7 (API v2) VID:PID 0483:3748
# Info : stm32f1x.cpu: hardware has 6 breakpoints, 4 watchpoints
```

```bash
# 终端2：启动 GDB
$ arm-none-eabi-gdb build/firmware.elf

# GDB 启动画面
# GNU Arm Embedded Toolchain ...
# Reading symbols from build/firmware.elf...
```

```gdb
# ====== 连接 ======
(gdb) target remote localhost:3333
# Remote debugging using localhost:3333
# 0x08000100 in Reset_Handler ()

(gdb) monitor reset halt
# target halted due to debug-request, current mode: Thread
# xPSR: 0x01000000 pc: 0x08000100

# ====== 打断点 ======
(gdb) break main
# Breakpoint 1 at 0x8000140: file src/main.c, line 7.

(gdb) break gpio_init
# Breakpoint 2 at 0x8000120: file src/main.c, line 3.

# ====== 运行到 main ======
(gdb) continue
# Continuing.
# Breakpoint 2, gpio_init () at src/main.c:3

# ====== 看看现在什么状态 ======
(gdb) info registers r0 r1 r2
# r0 = 0x00000000    r1 = 0x00000000    r2 = 0x00000000

(gdb) print RCC->APB2ENR
# $1 = 0x00000000    ← GPIOA 时钟还没开

# ====== 单步执行，看时钟开没开 ======
(gdb) next
# 4       RCC->APB2ENR |= RCC_APB2ENR_IOPAEN;

(gdb) next
# 5       GPIOA->CRL &= ~(0xF << 20);

(gdb) print RCC->APB2ENR
# $2 = 0x00000004    ← bit2 置 1，GPIOA 时钟已开 ✓

(gdb) print RCC->APB2ENR & RCC_APB2ENR_IOPAEN
# $3 = 4    ← 确认 IOPAEN 位被置位

# ====== 继续单步，看 GPIO 配置 ======
(gdb) next
# 6       GPIOA->CRL |=  (0x3 << 20);

(gdb) next
# 8       }

(gdb) print /x GPIOA->CRL
# $4 = 0x00300000    ← PA5 配置为推挽输出 50MHz ✓
#        ^^
#        bit[23:20] = 0x3 = MODE5=11(50MHz), CNF5=00(推挽)

(gdb) finish
# Run till exit from #0  gpio_init () at src/main.c:6
# 0x08000160 in main () at src/main.c:10

# ====== 进入主循环 ======
(gdb) next
# 11          GPIOA->ODR ^= (1 << 5);

(gdb) print /x GPIOA->ODR
# $5 = 0x00000000    ← LED 灭

(gdb) next
# 12          delay(500000);

(gdb) print /x GPIOA->ODR
# $6 = 0x00000020    ← PA5 高电平，LED 亮 ✓
#              ^
#              bit5 = 1

# ====== 设置观察点 ======
(gdb) watch GPIOA->ODR
# Hardware watchpoint 3: GPIOA->ODR

(gdb) continue
# Continuing.
# Hardware watchpoint 3: GPIOA->ODR
# Old value = 32    (0x20)
# New value = 0     (0x00)
# ← LED 灭了

# ====== 查看调用栈 ======
(gdb) backtrace
# #0  main () at src/main.c:11

# ====== 查看当前指令 ======
(gdb) x/3i $pc
# 0x8000160: ldr  r0, [pc, #20]    ; 加载 GPIOA->ODR 地址
# 0x8000162: ldr  r1, [r0, #0]
# 0x8000164: eor  r1, r1, #32      ; XOR bit5

# ====== 结束调试 ======
(gdb) monitor reset run
# 芯片正常运行（不暂停）

(gdb) quit
# 退出 GDB
```

### VS Code 图形化调试（推荐日常使用）

#### 安装扩展

```
VS Code 扩展商店搜索安装：
├── Cortex-Debug          ← ARM 调试核心插件
├── Cortex-Debug: Device Support Pack - STM32F1  ← 可选，SVD 支持
└── C/C++                 ← IntelliSense
```

#### 配置 launch.json

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "STM32 Debug",
            "type": "cortex-debug",
            "request": "launch",
            "servertype": "openocd",
            "executable": "${workspaceFolder}/build/firmware.elf",
            "configFiles": [
                "interface/stlink.cfg",
                "target/stm32f1x.cfg"
            ],
            "svdFile": "${workspaceFolder}/STM32F103xx.svd",
            "runToEntryPoint": "main",
            "showDevDebugOutput": "raw",
            "preLaunchTask": "build"
        }
    ]
}
```

#### 配置 tasks.json（编译任务）

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "build",
            "type": "shell",
            "command": "make",
            "group": {
                "kind": "build",
                "isDefault": true
            },
            "problemMatcher": ["$gcc"]
        }
    ]
}
```

#### 获取 SVD 文件（寄存器可视化神器）

```bash
# SVD 文件定义了芯片所有外设寄存器的名称、地址、位域
# 有了它，调试时可以在 VS Code 里像看表格一样查看寄存器

# 方法1：从 GitHub 下载
wget https://raw.githubusercontent.com/posborne/cmsis-svd/master/data/STMicro/STM32F103xx.svd
mv STM32F103xx.svd .

# 方法2：从 STM32CubeIDE 安装目录找
# Windows: C:\ST\STM32CubeIDE_xxx\plugins\com.st.stm32cube.common.mx_xxx\resources\cmsis\STMicro\
# Linux:   ~/.stm32cubemx/...
```

#### VS Code 调试界面

```
按 F5 启动调试，你会看到：

┌─────────────────────────────────────────────────────────────────────┐
│  VS Code                                                    ─ □ ✕  │
├─────────────────────────────────────────────────────────────────────┤
│  src/main.c                                                         │
│  1  #include "stm32f1xx.h"                                         │
│  2                                                                   │
│  3  void gpio_init(void) {                                          │
│  4      RCC->APB2ENR |= RCC_APB2ENR_IOPAEN;                        │
│  5      GPIOA->CRL &= ~(0xF << 20);                                │
│  6      GPIOA->CRL |=  (0x3 << 20);                                │
│  7  }                               │                               │
│  8                                  │ 亮黄色箭头 = 当前执行位置       │
│  9  void delay(volatile uint32_t n){│                               │
│ 10      while (n--) __asm__("nop");│ 红色圆点 = 断点                 │
│ 11  }                               ●                               │
│ 12                                  │                               │
│ 13  int main(void) {                ● ← 断点                        │
│ 14      gpio_init();                │                               │
│ 15      while (1) {                 │                               │
│ 16          GPIOA->ODR ^= (1 << 5);│                               │
│ 17          delay(500000);          │                               │
│ 18      }                           │                               │
│ 19  }                               │                               │
├──────────────────────┬──────────────┬───────────────────────────────┤
│ VARIABLE             │  CALL STACK  │  CORTEX PERIPHERALS           │
│                      │              │                               │
│  Local:              │  main()      │  ▼ RCC                       │
│    n = 500000        │  src/main.c  │    CR     = 0x00000083       │
│                      │  :13         │    CFGR   = 0x00000000       │
│  Global:             │              │    APB2ENR= 0x00000004       │
│                      │  Reset_Hdlr  │      IOPAEN = 1  ← GPIOA时钟│
│                      │  startup.s   │      IOPBEN = 0             │
│                      │  :42         │  ▼ GPIOA                     │
│                      │              │    CRL  = 0x00300000        │
│                      │              │      CNF5  = 00 (推挽输出)   │
│                      │              │      MODE5 = 11 (50MHz)     │
│                      │              │    CRH  = 0x44444444        │
│                      │              │    IDR  = 0x00000000        │
│                      │              │    ODR  = 0x00000020        │
│                      │              │      ODR5 = 1  ← LED亮     │
│                      │              │    BSRR = 0x00000000        │
│                      │              │    BRR  = 0x00000000        │
├──────────────────────┴──────────────┴───────────────────────────────┤
│ Debug Console                                                       │
│ > target remote localhost:3333                                       │
│ > monitor reset halt                                                 │
│ > Breakpoint 1, main () at src/main.c:13                            │
└─────────────────────────────────────────────────────────────────────┘

顶部调试工具栏：
  ▶ Continue    ⏭ Step Over    ⬇ Step Into    ⬆ Step Out    ↻ Restart    ■ Stop
```

**Cortex Peripherals 面板**就是 SVD 文件提供的，它把寄存器的每一位都展开显示，比手动 `print` 高效得多。

### 调试技巧速查

#### 常用 GDB 命令速查表

```
┌──────────────────────┬────────────────────────────────────────┐
│      命令             │      作用                              │
├──────────────────────┼────────────────────────────────────────┤
│  连接 & 控制                                       │
│  target remote :3333 │  连接 OpenOCD                        │
│  monitor reset halt  │  复位并暂停                           │
│  monitor reset run   │  复位并运行                           │
│  continue (c)        │  继续运行                             │
│  quit (q)            │  退出 GDB                             │
├──────────────────────┼────────────────────────────────────────┤
│  断点                                            │
│  break main          │  在 main 函数打断点                    │
│  break file.c:10     │  在 file.c 第 10 行打断点              │
│  break func_name     │  在函数入口打断点                      │
│  delete 1            │  删除 1 号断点                         │
│  delete              │  删除所有断点                          │
│  info break          │  列出所有断点                          │
├──────────────────────┼────────────────────────────────────────┤
│  单步执行                                          │
│  next (n)            │  执行一行，不进函数                    │
│  step (s)            │  执行一行，进函数                      │
│  finish              │  执行到函数返回                        │
│  nexti (ni)          │  执行一条汇编指令                      │
│  stepi (si)          │  执行一条汇编，跳转时跟进去             │
├──────────────────────┼────────────────────────────────────────┤
│  查看信息                                          │
│  print (p) expr      │  打印表达式值                          │
│  print /x var        │  十六进制打印                          │
│  print /t var        │  二进制打印                            │
│  print RCC->APB2ENR  │  读外设寄存器                          │
│  display var         │  每次暂停自动显示                       │
│  info locals         │  所有局部变量                          │
│  info registers      │  CPU 寄存器                            │
│  backtrace (bt)      │  调用栈                               │
│  x/Nfx addr          │  查看内存                              │
│  x/10i $pc           │  反汇编当前 10 条指令                   │
│  list (l)            │  显示当前源码上下文                     │
├──────────────────────┼────────────────────────────────────────┤
│  观察点                                            │
│  watch var           │  变量值改变时暂停                       │
│  rwatch var          │  变量被读取时暂停                       │
│  awatch var          │  变量被读或写时暂停                     │
├──────────────────────┼────────────────────────────────────────┤
│  修改                                              │
│  set var = value     │  修改变量值                            │
│  set GPIOA->ODR = 0  │  写外设寄存器                          │
│  set $pc = addr      │  修改 PC（跳转）                       │
└──────────────────────┴────────────────────────────────────────┘
```

### 调试时编译选项要切换

```makefile
# ============ 调试版（开发时用）============
CFLAGS = $(MCU) -D$(DEVICE) $(INCLUDES) \
         -Wall -fdata-sections -ffunction-sections \
         -g -O0
#        ^^^^
#        -g   加调试信息（行号、变量名）
#        -O0  关优化（变量值不会被优化掉，断点不会乱跳）

# ============ 发布版（烧给客户时用）============
CFLAGS = $(MCU) -D$(DEVICE) $(INCLUDES) \
         -Wall -fdata-sections -ffunction-sections \
         -Os
#        ^^^^
#        -Os  体积优化（不带调试信息，体积更小）
```

#### -O0 和 -Os 调试体验对比

```c
int a = 1;
int b = a + 2;
int c = b * 3;
```

```
-O0 调试时：
  next → 停在 int a = 1;      print a → 未初始化
  next → 停在 int b = a + 2;  print a → 1
  next → 停在 int c = b * 3;  print b → 3
  next → 停在 ...              print c → 9
  每行都能停，每个变量都能看值                ✓

-Os 调试时：
  next → 直接跳过好几行
  print a → <optimized out>
  print b → <optimized out>
  编译器把三行合并成一行了，变量被优化没了    ✗
```

### 硬件调试能力（STM32 内置）

```
Cortex-M3 内置的调试硬件资源：

断点（Breakpoint）：6 个
├── 硬件实现，不修改代码
├── 在 Flash 中执行时必须用硬件断点
└── break 命令自动使用

观察点（Watchpoint）：4 个
├── 监视内存地址的读写
├── watch my_variable 用的就是这个
└── 嵌入式调试中非常有用（监听硬件寄存器变化）

DWT 周期计数器：
├── 精确测量代码执行时间
└── monitor mdw 0xE0001004 读取周期数
```

```gdb
# 用 GDB 测量函数执行时间
(gdb) monitor mdw 0xE0001004     # 读当前周期数
0xe0001004: 00001234

(gdb) break after_function       # 在函数后面打断点

(gdb) continue
# ... 函数执行完毕 ...

(gdb) monitor mdw 0xE0001004     # 再读周期数
0xe0001004: 00056789

# 执行了 0x56789 - 0x1234 = 0x55555 = 349525 个时钟周期
# 如果时钟 72MHz，耗时 = 349525 / 72000000 = 4.85ms
```

### 日常调试流程总结

```
发现程序运行异常
      │
      ├── 症状明确（比如 LED 不亮）
      │     │
      │     ├── 简单问题 → printf 重定向到串口打印变量值
      │     │              （快，但需要 UART 硬件）
      │     │
      │     └── 复杂问题 → GDB 断点调试
      │                    1. 在可疑位置打断点
      │                    2. 单步执行
      │                    3. 查看寄存器/变量/内存
      │                    4. 找到问题
      │
      └── 症状不明确（偶发崩溃、死循环）
            │
            ├── HardFault → 查看调用栈、LR、PC
            │                x/4xw 0xE000ED24  （查看故障状态寄存器）
            │
            └── 逻辑错误 → 观察点（watch）
                           监视关键变量的意外修改
```

**日常开发建议：VS Code + Cortex-Debug + SVD 文件，图形化调试效率最高。命令行 GDB 作为备选和深入调试手段。**

## 注意事项 & 踩坑

- 调试时必须用 `-O0 -g` 编译，否则变量值显示 `<optimized out>`
- 硬件断点只有 6 个，超过会报错
- 观察点只有 4 个，且必须是硬件支持的地址范围
- OpenOCD 必须保持运行，关闭后 GDB 会断开连接

## 相关笔记

- [[STM32寄存器开发概述]]
- [[STM32寄存器开发构建过程详解]]
- [[Makefile基础与进阶]]
- [[STM32寄存器级调试实战]]
- [[GDB调试命令详解]]
- [[Ubuntu 24.04调试器配置]]

## 参考来源

- OpenOCD 官方文档
- GDB 官方手册
- Cortex-Debug VS Code 扩展文档
- ARM CoreSight 调试架构文档
