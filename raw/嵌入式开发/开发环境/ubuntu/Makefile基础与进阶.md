---
title: "Makefile基础与进阶"
category: "STM32/开发环境"
tags: [Makefile, 构建系统, 自动化编译]
abstract: "详解STM32项目Makefile的编写原理、语法和演进过程"
source: "原创"
update_time: 2026-05-28
status: 完成
type: 原理
---

## 一句话定义

Makefile是STM32项目的构建系统核心，通过变量、依赖关系、模式规则等机制实现自动化编译、增量构建和死代码删除。

## 核心内容

### 完整Makefile模板（自动收集源文件版）

```makefile
# ============ 工具链 ============
PREFIX  = arm-none-eabi-
CC      = $(PREFIX)gcc
AS      = $(PREFIX)gcc -x assembler-with-cpp
OBJCOPY = $(PREFIX)objcopy
SIZE    = $(PREFIX)size
RM      = rm -rf

# ============ 目标 ============
TARGET  = firmware
BUILD   = build

# ============ 芯片定义 ============
DEVICE  = STM32F103xB
MCU     = -mcpu=cortex-m3 -mthumb

# ============ 自动收集源文件（★ 核心改动 ★） ============
# 递归查找 src/ 下所有 .c 文件
C_SOURCES   = $(shell find src -name '*.c')

# 查找所有汇编文件
ASM_SOURCES = $(shell find . -name '*.s')

# ============ 自动收集头文件路径 ============
# 递归查找所有包含 .h 文件的目录
INCLUDES = -ICMSIS $(addprefix -I, $(sort $(dir $(shell find inc -name '*.h'))))

# ============ 编译选项 ============
CFLAGS  = $(MCU) -D$(DEVICE) $(INCLUDES) -Wall -fdata-sections -ffunction-sections -Os -MMD -MP
LDFLAGS = $(MCU) -T STM32F103C8Tx_FLASH.ld -Wl,--gc-sections -specs=nosys.specs -lm

# ============ 自动构建目标文件列表 ============
# 把 src/drivers/gpio.c → build/gpio.o
C_OBJECTS   = $(addprefix $(BUILD)/, $(notdir $(C_SOURCES:.c=.o)))
ASM_OBJECTS = $(addprefix $(BUILD)/, $(notdir $(ASM_SOURCES:.s=.o)))
OBJECTS     = $(C_OBJECTS) $(ASM_OBJECTS)

# ============ VPATH：告诉 make 去哪里找源文件 ============
VPATH = $(sort $(dir $(C_SOURCES))) $(sort $(dir $(ASM_SOURCES)))

# ============ 最终输出文件 ============
ELF = $(BUILD)/$(TARGET).elf
BIN = $(BUILD)/$(TARGET).bin
HEX = $(BUILD)/$(TARGET).hex

# ============================================================
#  构建规则
# ============================================================

# 默认目标：生成 .elf、.bin、.hex 三个文件
all: $(ELF) $(BIN) $(HEX)
	$(SIZE) $(ELF)

# ---- Step 1: 链接 → .elf ----
$(ELF): $(OBJECTS)
	$(CC) $(LDFLAGS) $^ -o $@

# ---- Step 2: .elf → .bin ----
$(BIN): $(ELF)
	$(OBJCOPY) -O binary $< $@

# ---- Step 3: .elf → .hex ----
$(HEX): $(ELF)
	$(OBJCOPY) -O ihex $< $@

# ---- 编译 .c → .o ----
$(BUILD)/%.o: %.c | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

# ---- 编译 .s → .o ----
$(BUILD)/%.o: %.s | $(BUILD)
	$(AS) $(MCU) -c $< -o $@

# ---- 创建构建目录 ----
$(BUILD):
	mkdir -p $(BUILD)

# ============================================================
#  常用命令
# ============================================================

clean:
	$(RM) $(BUILD)

flash: $(HEX)
	openocd -f interface/stlink.cfg -f target/stm32f1x.cfg \
		-c "program $(HEX) verify reset exit"

debug: $(ELF)
	openocd -f interface/stlink.cfg -f target/stm32f1x.cfg &
	$(PREFIX)gdb $(ELF) -ex "target remote :3333" -ex "monitor reset halt"

# ============ 自动依赖 ============
-include $(OBJECTS:.o=.d)

.PHONY: all clean flash debug
```

### 逐行详解

#### 第一段：工具链定义

```makefile
PREFIX  = arm-none-eabi-
CC      = $(PREFIX)gcc
AS      = $(PREFIX)gcc -x assembler-with-cpp
OBJCOPY = $(PREFIX)objcopy
SIZE    = $(PREFIX)size
RM      = rm -rf
```

**语法点：变量赋值**

```makefile
# Makefile 中只有一种赋值符号：=
# 但配合不同场景有不同行为

PREFIX = arm-none-eabi-
#      ^
#      普通赋值（递归展开）
# 在 $(PREFIX) 被使用时才展开，不是定义时

CC = $(PREFIX)gcc
#    ^^^^^^^^^
#    使用时展开为 arm-none-eabi-gcc
```

#### 第二段：构建目标

```makefile
TARGET  = firmware
BUILD   = build
```

- `TARGET`：最终输出文件的基础名，最终生成 `build/firmware.elf` → `build/firmware.bin`
- `BUILD`：构建输出目录，所有 `.o`、`.elf`、`.bin`、`.d` 都放在这里

#### 第三段：芯片定义

```makefile
DEVICE  = STM32F103xB
MCU     = -mcpu=cortex-m3 -mthumb
```

- `DEVICE`：传递给预处理器的宏定义，最终变成编译参数 `-DSTM32F103xB`
- `MCU`：告诉编译器目标CPU架构和指令集

#### 第四段：自动收集源文件

```makefile
C_SOURCES   = $(shell find src -name '*.c')
ASM_SOURCES = $(shell find . -name '*.s')
```

**语法点：`$(shell ...)`**

```makefile
# $(shell command) 执行 shell 命令，把 stdout 作为结果赋值
# 相当于在终端执行命令，把输出拿回来当变量值

C_SOURCES = $(shell find src -name '*.c')
#  等价于在终端执行：find src -name '*.c'
#  输出（举例）：
#    src/main.c
#    src/system_stm32f1xx.c
#    src/drivers/gpio.c
#    src/drivers/uart.c
#    src/app/control.c
```

#### 第五段：自动收集头文件路径

```makefile
INCLUDES = -ICMSIS $(addprefix -I, $(sort $(dir $(shell find inc -name '*.h'))))
```

这行嵌套很深，从内向外拆解：

```makefile
# ========== 从内到外，逐层拆解 ==========

# 第1层：shell 命令
$(shell find inc -name '*.h')
# 输出：
#   inc/main.h
#   inc/drivers/gpio.h
#   inc/drivers/uart.h
#   inc/app/control.h

# 第2层：$(dir ...)

### 语法点：$(dir <names>)
# 提取文件路径中的目录部分
$(dir inc/main.h inc/drivers/gpio.h inc/app/control.h)
# 输出：
#   inc/ inc/drivers/ inc/app/

# 第3层：$(sort ...)

### 语法点：$(sort <list>)
# 排序 + 去重
$(sort inc/ inc/drivers/ inc/drivers/ inc/app/)
# 输出（去重排序后）：
#   inc/ inc/app/ inc/drivers/

# 第4层：$(addprefix -I, ...)

### 语法点：$(addprefix <prefix>, <list>)
# 给列表中每一项添加前缀
$(addprefix -I, inc/ inc/app/ inc/drivers/)
# 输出：
#   -Iinc/ -Iinc/app/ -Iinc/drivers/

# 第5层：拼上 CMSIS
INCLUDES = -ICMSIS -Iinc/ -Iinc/app/ -Iinc/drivers/
# 最终效果：编译器会在这些目录中搜索 #include 的头文件
```

#### 第六段：编译选项

```makefile
CFLAGS  = $(MCU) -D$(DEVICE) $(INCLUDES) -Wall -fdata-sections -ffunction-sections -Os -MMD -MP
LDFLAGS = $(MCU) -T STM32F103C8Tx_FLASH.ld -Wl,--gc-sections -specs=nosys.specs -lm
```

**CFLAGS 逐个参数：**

```
$(MCU)                   → -mcpu=cortex-m3 -mthumb
                           目标 CPU 和指令集

-D$(DEVICE)              → -DSTM32F103xB
                           定义预处理宏，等价于在代码开头写 #define STM32F103xB

$(INCLUDES)              → -ICMSIS -Iinc/ -Iinc/drivers/ ...
                           头文件搜索路径

-Wall                    → 开启所有常用警告
                           不影响编译结果，但帮你发现潜在问题

-fdata-sections          → 每个全局变量放入独立的 Section
                           配合链接时 --gc-sections 删除未使用的变量

-ffunction-sections      → 每个函数放入独立的 Section
                           配合链接时 --gc-sections 删除未调用的函数

-Os                      → 优化级别：体积优先
                           嵌入式 Flash 有限，通常选 Os
                           -O0 不优化（调试用）
                           -O1 基本优化
                           -O2 较强优化
                           -O3 最强优化（可能增大体积）
                           -Os 体积优化

-MMD                     → 自动生成依赖文件（.d）
                           编译 main.c 时生成 main.d
                           main.d 内容：main.o: main.c gpio.h uart.h
                           当 gpio.h 修改时，make 知道要重编 main.c

-MP                      → 为每个依赖目标生成伪目标
                           main.d 内容会多一行：gpio.h:
                           防止删除头文件后 make 报错
```

**LDFLAGS 逐个参数：**

```
$(MCU)                    → -mcpu=cortex-m3 -mthumb
                            链接器也需要知道目标架构

-T STM32F103C8Tx_FLASH.ld → 指定链接脚本
                            定义 Flash/RAM 地址、Section 布局

-Wl,--gc-sections         → -Wl,<option> 把 <option> 传给链接器
                            --gc-sections 删除未被引用的 Section
                            配合编译时的 -fdata-sections
                            和 -ffunction-sections 使用
                            效果：没调用的函数不会进入最终固件

-specs=nosys.specs        → 裸机开发用
                            不依赖操作系统的系统调用
                            标准库函数（如 printf）需要的
                            _sbrk、_write、_read 等
                            提供空实现（桩函数）

-lm                       → 链接数学库 libm
                            使用 sin()、cos()、sqrt() 等时需要
```

#### 第七段：构建目标文件列表

```makefile
C_OBJECTS   = $(addprefix $(BUILD)/, $(notdir $(C_SOURCES:.c=.o)))
ASM_OBJECTS = $(addprefix $(BUILD)/, $(notdir $(ASM_SOURCES:.s=.o)))
OBJECTS     = $(C_OBJECTS) $(ASM_OBJECTS)
```

**逐层拆解：**

```makefile
# ========== C_OBJECTS 的生成过程 ==========

# C_SOURCES 的值：
#   src/main.c src/system_stm32f1xx.c src/drivers/gpio.c src/app/control.c

# 第1层：$(C_SOURCES:.c=.o)

### 语法点：$(var:后缀=新后缀)  后缀替换
# 把变量中每一项的 .c 替换成 .o
$(C_SOURCES:.c=.o)
# 输出：
#   src/main.o src/system_stm32f1xx.o src/drivers/gpio.o src/app/control.o

# 第2层：$(notdir ...)

### 语法点：$(notdir <names>)  去掉目录，只留文件名
$(notdir src/main.o src/drivers/gpio.o)
# 输出：
#   main.o gpio.o

# 第3层：$(addprefix build/, ...)

### 语法点：$(addprefix <prefix>, <list>)  加前缀
$(addprefix build/, main.o gpio.o)
# 输出：
#   build/main.o build/gpio.o

# 完整展开：
C_OBJECTS = build/main.o build/system_stm32f1xx.o build/gpio.o build/control.o

# ASM_OBJECTS 同理，把 .s 替换成 .o
ASM_OBJECTS = build/startup_stm32f103xb.o

# 最终合并
OBJECTS = build/main.o build/system_stm32f1xx.o build/gpio.o build/control.o build/startup_stm32f103xb.o
```

#### 第八段：VPATH（源文件搜索路径）

```makefile
VPATH = $(sort $(dir $(C_SOURCES))) $(sort $(dir $(ASM_SOURCES)))
```

**语法点：VPATH**

```makefile
# VPATH 告诉 make："当找不到文件时，去这些目录中搜索"
#
# 问题场景：
#   构建规则写的是  $(BUILD)/%.o: %.c
#   要构建 build/gpio.o，make 需要找 gpio.c
#   但 gpio.c 在 src/drivers/ 下，当前目录没有
#
# 没有 VPATH 时：make 报错 "No rule to make target 'gpio.c'"
# 有 VPATH 时：  make 去 src/ src/drivers/ src/app/ 里找
#                找到 src/drivers/gpio.c，匹配成功

# 没有 VPATH 的话，每个子目录都要写一条规则：
#   $(BUILD)/%.o: src/%.c          # 只能匹配 src/ 下的文件
#   $(BUILD)/%.o: src/drivers/%.c  # 要额外加这条
#   $(BUILD)/%.o: src/app/%.c      # 还要加这条
#   ...每加一个目录就要加一条
#
# 有了 VPATH，一条规则搞定所有目录
```

#### 第九段：构建规则

```makefile
$(BUILD)/$(TARGET).elf: $(OBJECTS)
	$(CC) $(LDFLAGS) $^ -o $@
	$(SIZE) $@

$(BUILD)/%.o: %.c | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD)/%.o: %.s | $(BUILD)
	$(AS) $(MCU) -c $< -o $@

$(BUILD):
	mkdir -p $(BUILD)
```

**语法点：规则的基本结构**

```makefile
目标: 依赖
	命令1
	命令2

# 目标（target）：要生成的文件
# 依赖（prerequisites）：目标所依赖的文件，任一依赖更新则重新执行命令
# 命令（recipe）：生成目标的 shell 命令，必须以 TAB 开头（不能是空格）
```

**语法点：自动变量**

```
$@    → 目标文件名      → build/firmware.elf
$^    → 所有依赖文件    → build/main.o build/gpio.o build/startup.o
$<    → 第一个依赖文件  → build/main.o（规则二中是 %.c）
```

**语法点：`%` 通配符（模式规则）**

```makefile
$(BUILD)/%.o: %.c
# % 是通配符，匹配任意字符串
# 当 make 需要 build/gpio.o 时：
#   % 匹配 gpio
#   目标：build/gpio.o
#   依赖：gpio.c（配合 VPATH 去 src/drivers/ 中找到）
#
# 等价于为每个 .c 文件隐式生成一条规则：
#   build/main.o: main.c
#   build/gpio.o: gpio.c
#   build/control.o: control.c
#   ...（自动生成，不用手写）
```

**语法点：`|` 顺序依赖（Order-only Prerequisite）**

```makefile
$(BUILD)/%.o: %.c | $(BUILD)
#                 ^^^^^^^^
#                 | 后面是"顺序依赖"
#
# 普通依赖：依赖文件更新了 → 重新构建目标
# 顺序依赖：只要依赖存在就行，更新了也不触发重新构建
#
# 为什么需要？
#   build/ 目录必须存在才能往里面写 .o 文件
#   但目录的"更新时间"在往里写文件时会变
#   如果用普通依赖，目录一变所有 .o 都要重新编译
#   用顺序依赖：目录存在即可，不会因为目录时间戳变化而重编
```

#### 第十段：清理 & 烧录 & 调试

```makefile
clean:
	$(RM) $(BUILD)

flash: $(BUILD)/$(TARGET).elf
	openocd -f interface/stlink.cfg -f target/stm32f1x.cfg \
		-c "program $< verify reset exit"

debug: $(BUILD)/$(TARGET).elf
	openocd -f interface/stlink.cfg -f target/stm32f1x.cfg &
	$(PREFIX)gdb $< -ex "target remote :3333" -ex "monitor reset halt"
```

#### 第十一段：自动依赖包含

```makefile
-include $(OBJECTS:.o=.d)
```

**语法点：`-include` 和后缀替换**

```makefile
# $(OBJECTS:.o=.d)  后缀替换
# build/main.o → build/main.d
# build/gpio.o → build/gpio.d
# ...

# -include 把这些 .d 文件包含进 Makefile
# - 前缀表示：如果文件不存在也不要报错
#   （首次编译时 .d 文件还不存在）

# 效果：
#   main.d 内容：build/main.o: src/main.c inc/main.h inc/drivers/gpio.h
#   被 include 后，make 知道 main.o 依赖 gpio.h
#   修改 gpio.h → make 自动重编 main.o
```

#### 第十二段：伪目标声明

```makefile
.PHONY: clean flash debug
```

**语法点：`.PHONY`**

```makefile
# 问题：如果你的目录下碰巧有个文件叫 clean
# 当你执行 make clean 时，make 检查：
#   "clean 文件已存在，且没有依赖，不需要执行任何命令"
#   于是什么都不做！

# .PHONY 告诉 make：clean、flash、debug 不是真实文件
# 它们是"动作"，每次都要执行，不管同名文件是否存在

.PHONY: clean flash debug
```

### 为什么要这么写Makefile

#### 核心思路：一切设计都是为了解决具体问题

先从最朴素的做法开始，遇到问题，解决问题，一步步演化到最终版本。

#### 第一步：没有 Makefile 时，你怎么做

```bash
# 你每次都手动敲这些命令
arm-none-eabi-gcc -mcpu=cortex-m3 -mthumb -DSTM32F103xB -ICMSIS -Iinc \
    -Os -fdata-sections -ffunction-sections \
    -c src/main.c -o build/main.o

arm-none-eabi-gcc -mcpu=cortex-m3 -mthumb -DSTM32F103xB -ICMSIS -Iinc \
    -Os -fdata-sections -ffunction-sections \
    -c src/gpio.c -o build/gpio.o

arm-none-eabi-gcc -mcpu=cortex-m3 -mthumb \
    -c startup_stm32f103xb.s -o build/startup.o

arm-none-eabi-gcc -mcpu=cortex-m3 -mthumb \
    -T STM32F103C8Tx_FLASH.ld -Wl,--gc-sections -specs=nosys.specs \
    build/main.o build/gpio.o build/startup.o -o build/firmware.elf

arm-none-eabi-objcopy -O binary build/firmware.elf build/firmware.bin

openocd -f interface/stlink.cfg -f target/stm32f1x.cfg \
    -c "program build/firmware.elf verify reset exit"
```

**痛点：**

- 命令太长，每次都打一遍
- 改一行代码，所有文件都要重新编译
- 文件多了，手动管理编译顺序容易出错
- 换个项目又要重新敲一遍

**所以 Makefile 的第一层意义：把重复的命令自动化。**

#### 问题① → 依赖关系：告诉 make "谁变了，谁要重编"

```makefile
# 拆成独立的规则，每个 .o 只依赖自己的 .c

build/main.o: src/main.c
	arm-none-eabi-gcc ... -c src/main.c -o build/main.o

build/gpio.o: src/gpio.c
	arm-none-eabi-gcc ... -c src/gpio.c -o build/gpio.o

build/startup.o: startup_stm32f103xb.s
	arm-none-eabi-gcc ... -c startup_stm32f103xb.s -o build/startup.o

build/firmware.elf: build/main.o build/gpio.o build/startup.o
	arm-none-eabi-gcc ... build/main.o build/gpio.o build/startup.o -o build/firmware.elf
```

```
现在 make 的逻辑：

改了 main.c
├── main.c 比 main.o 新？ → 重编 main.o
├── gpio.c 比 gpio.o 新？ → 不用动
├── 任何 .o 比 .elf 新？   → 重新链接
└── 只编译了 main.o，省了 gpio.o 的编译时间  ✓
```

**这就是"依赖树"的意义：增量编译，只编译变了的东西。**

#### 问题② → 变量：消除重复

```makefile
# 之前：每个规则都写一遍 -mcpu=cortex-m3 -mthumb -DSTM32F103xB ...
# 改芯片型号要改 4 个地方

# 之后：提取变量
MCU    = -mcpu=cortex-m3 -mthumb
DEVICE = STM32F103xB
CFLAGS = $(MCU) -D$(DEVICE) -ICMSIS -Iinc -Os ...

build/main.o: src/main.c
	$(CC) $(CFLAGS) -c $< -o $@

build/gpio.o: src/gpio.c
	$(CC) $(CFLAGS) -c $< -o $@
```

```
改芯片型号时：
├── 改 DEVICE = STM32F407xE
├── 改 MCU = -mcpu=cortex-m4 -mthumb
├── 换链接脚本
└── 所有规则自动更新           ✓
```

**变量的意义：一处定义，处处生效。**

#### 问题③ → 模式规则：消除规则的重复

```makefile
# 之前：每个 .c 文件写一条规则
build/main.o: src/main.c
	$(CC) $(CFLAGS) -c $< -o $@

build/gpio.o: src/gpio.c
	$(CC) $(CFLAGS) -c $< -o $@

build/uart.o: src/uart.c
	$(CC) $(CFLAGS) -c $< -o $@

build/timer.c: src/timer.c
	$(CC) $(CFLAGS) -c $< -o $@
# 这四条规则结构完全一样，只是文件名不同

# 之后：用 % 通配符，一条规则覆盖所有
$(BUILD)/%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@
```

**模式规则的意义：N 条相同结构的规则压缩成 1 条。**

#### 问题④ → 源文件列表：新增文件要改 Makefile

```
场景：你新写了 src/uart.c

问题：链接时需要 uart.o，但 make 不知道 uart.c 的存在
      C_SOURCES 里没有 src/uart.c → 没有 build/uart.o → 链接报错 undefined reference

方案 A（手动）：在 C_SOURCES 里加一行 src/uart.c
方案 B（自动）：让 make 自己去找
```

```makefile
# 方案 A：手动列举
C_SOURCES = src/main.c src/gpio.c src/uart.c src/timer.c
#           ↑ 每次新增文件都要来加一行

# 方案 B：自动收集
C_SOURCES = $(shell find src -name '*.c')
#           ↑ 不管你怎么加文件，自动找到                ✓
```

**自动收集的意义：新增文件零改动。**

#### 问题⑤ → 子目录 + VPATH：代码组织变复杂

```
项目大了，代码分目录放：
src/
├── main.c
├── drivers/
│   ├── gpio.c
│   └── uart.c
└── app/
    └── control.c
```

```makefile
# 没有 VPATH 时，要为每个目录写规则：
$(BUILD)/%.o: src/%.c            # 只能找到 src/ 下的
$(BUILD)/%.o: src/drivers/%.c    # 要加这条
$(BUILD)/%.o: src/app/%.c        # 还要加这条
# 每加一个目录就要加一条规则

# 有 VPATH 后：一条规则搞定
VPATH = src/ src/drivers/ src/app/
$(BUILD)/%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@
```

```
make 找文件的过程：

需要 build/gpio.o → 需要 gpio.c
├── 当前目录有 gpio.c 吗？→ 没有
├── VPATH 说去 src/ 找    → 没有
├── VPATH 说去 src/drivers/ 找 → 找到了！
└── 匹配 %.c 规则，开始编译
```

**VPATH 的意义：无论代码怎么分目录，编译规则不变。**

#### 问题⑥ → -MMD -MP：头文件依赖

```c
// main.c
#include "gpio.h"    // 依赖 gpio.h

void main() {
    gpio_init();
}
```

```
问题场景：
  第1次编译 → main.o 生成 ✓
  你改了 gpio.h 中的某个函数声明
  再次 make → make 检查：main.c 没变，main.o 不用重编  ✗

  链接时用的是旧的 main.o，和新的 gpio.c 对不上，运行出错
```

```makefile
# 解决：编译时让 gcc 自动分析 #include 依赖
CFLAGS = ... -MMD -MP

# 编译 main.c 时，gcc 自动在 build/main.d 中写入：
# build/main.o: src/main.c inc/main.h inc/drivers/gpio.h

# Makefile 末尾：
-include $(OBJECTS:.o=.d)
# 把 .d 文件内容导入 make，make 就知道了完整的依赖链
```

```
现在 make 的逻辑：

你改了 gpio.h
├── 检查 main.d：main.o 依赖 gpio.h
├── gpio.h 比 main.o 新？ → 重编 main.o    ✓
├── 检查 gpio.d：gpio.o 依赖 gpio.h
├── gpio.h 比 gpio.o 新？ → 重编 gpio.o    ✓
└── 链接
```

**自动依赖的意义：改头文件不会遗漏重编。**

#### 问题⑦ → 顺序依赖 `|`：构建目录的时间戳

```makefile
# 天真的写法：
$(BUILD)/%.o: %.c $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

# 问题：每次往 build/ 写入一个 .o 文件
# build/ 目录的 mtime 就更新一次
# make 发现 build/ 比所有 .o 都新
# 认为所有 .o 都需要重新编译 → 全量重编   ✗
```

```makefile
# 正确写法：
$(BUILD)/%.o: %.c | $(BUILD)
#                 ^^^^^^^^^
#                 顺序依赖：build/ 存在即可，mtime 变化不触发重编

$(BUILD):
	mkdir -p $(BUILD)
# 只在 build/ 不存在时创建，不会反复触发
```

**`|` 的意义：目录只是容器，不该影响编译判断。**

#### 问题⑧ → -fdata-sections + --gc-sections：删除死代码

```c
// util.c
void useful_func(void) { ... }
void unused_func(void) { ... }    // 从来没人调用

// main.c
extern void useful_func(void);
int main() { useful_func(); }
```

```makefile
# 没有 gc-sections 时：
#   util.o 中两个函数都被链接进固件
#   unused_func 白白占 Flash 空间

# 有 gc-sections 时：
CFLAGS  = ... -fdata-sections -ffunction-sections    # 每个函数独立一个 Section
LDFLAGS = ... -Wl,--gc-sections                       # 链接时删除无引用的 Section

# unused_func 没人引用 → 链接器丢弃 → Flash 更小
```

```
固件体积对比（典型项目）：
  不用 gc-sections：12.3 KB
  使用 gc-sections： 9.1 KB    ← 省了 26%

  对于只有 64KB Flash 的 STM32F103C8，这很重要
```

**gc-sections 的意义：嵌入式 Flash 寸土寸金，没用的代码不进固件。**

#### 问题⑨ → .PHONY：假想的文件名冲突

```makefile
# 假设你的目录下碰巧有个文件叫 "clean"
$ ls
clean    src/    Makefile

# 执行 make clean 时，make 的逻辑：
#   "clean 文件已存在，没有依赖，没有需要更新的"
#   → 什么都不做   ✗

# 声明伪目标后：
.PHONY: clean
# make 知道 clean 不是文件名，是动作名
# 每次都执行 rm -rf build   ✓
```

### 完整演化路线

```
阶段1：手动敲命令
  痛点：太长、太重复
  ↓
阶段2：朴素 Makefile（把命令搬到文件里）
  痛点：改一行全量重编
  ↓
阶段3：拆分依赖关系（每个 .o 依赖自己的 .c）
  痛点：参数重复写
  ↓
阶段4：提取变量（CC, CFLAGS, MCU...）
  痛点：每个文件一条规则
  ↓
阶段5：模式规则（%.o: %.c）
  痛点：新增文件要改 Makefile
  ↓
阶段6：自动收集 + VPATH（find + VPATH）
  痛点：改头文件不触发重编
  ↓
阶段7：自动依赖（-MMD -MP + -include .d）
  痛点：目录时间戳干扰
  ↓
阶段8：顺序依赖（| $(BUILD)）
  痛点：死代码占空间
  ↓
阶段9：gc-sections（-fdata-sections + -Wl,--gc-sections）
  痛点：假想文件名冲突
  ↓
阶段10：.PHONY
  ✓ 最终版本
```

### 一句话总结每个设计决策

```
为什么要变量？           → 一个参数改一处，不是 N 处
为什么要依赖关系？        → 只编译变了的文件
为什么要模式规则？        → N 条相同规则压缩成 1 条
为什么要 find？          → 新增文件零改动
为什么要 VPATH？         → 子目录不影响编译规则
为什么要 -MMD？          → 改头文件不会漏编
为什么要顺序依赖 | ？    → 目录不该触发重编
为什么要 gc-sections？   → 删掉没用的代码，省 Flash
为什么要 .PHONY？        → 告诉 make "这是动作，不是文件"
```

**每个语法都是某个真实问题的解法，不是为了写得"高级"。**

### 随代码增长的修改指南

#### 场景一：新增 `.c` 源文件（最频繁）

```
项目结构变化：
src/
├── main.c
├── system_stm32f1xx.c
├── gpio.c          ← 新增
├── uart.c          ← 新增
└── timer.c         ← 新增
```

**改这一行：**

```makefile
# 改之前
C_SOURCES = src/main.c src/system_stm32f1xx.c

# 改之后
C_SOURCES = src/main.c \
            src/system_stm32f1xx.c \
            src/gpio.c \
            src/uart.c \
            src/timer.c
```

**如果忘了改会怎样？**

```bash
# 链接时报错：undefined reference to 'uart_init'
# 原因：uart.c 没编译，uart_init 函数根本没生成 .o
```

#### 场景二：新增子目录

```
项目结构变化：
src/
├── main.c
├── drivers/         ← 新增目录
│   ├── gpio.c
│   ├── uart.c
│   └── timer.c
└── app/
    └── control.c    ← 新增目录
```

**需要改两处：**

```makefile
# ① C_SOURCES 加上新路径
C_SOURCES = src/main.c \
            src/system_stm32f1xx.c \
            src/drivers/gpio.c \
            src/drivers/uart.c \
            src/drivers/timer.c \
            src/app/control.c

# ② 新增构建规则（因为路径变了，原来的 src/%.c 匹配不到子目录）
# 旧规则只能匹配 src/xxx.c，匹配不到 src/drivers/xxx.c
$(BUILD)/%.o: src/%.c | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

# 需要新增：
$(BUILD)/%.o: src/drivers/%.c | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD)/%.o: src/app/%.c | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@
```

**这太麻烦了。下面给出一劳永逸的解决方案。**

#### 场景三：新增头文件搜索路径

```
inc/
├── main.h
├── drivers/         ← 新增
│   ├── gpio.h
│   └── uart.h
└── app/             ← 新增
    └── control.h
```

```makefile
# 改之前
INCLUDES = -ICMSIS -Iinc

# 改之后
INCLUDES = -ICMSIS -Iinc -Iinc/drivers -Iinc/app
```

**如果忘了改会怎样？**

```c
// uart.c 中写了
#include "gpio.h"   // ← 编译报错: gpio.h: No such file or directory
```

#### 一劳永逸的 Makefile（自动收集源文件）

这是**关键升级**。改完后，新增 `.c` 文件再也不需要动 Makefile。

```makefile
# ============ 工具链 ============
PREFIX  = arm-none-eabi-
CC      = $(PREFIX)gcc
AS      = $(PREFIX)gcc -x assembler-with-cpp
OBJCOPY = $(PREFIX)objcopy
SIZE    = $(PREFIX)size
RM      = rm -rf

# ============ 目标 ============
TARGET  = firmware
BUILD   = build

# ============ 芯片定义 ============
DEVICE  = STM32F103xB
MCU     = -mcpu=cortex-m3 -mthumb

# ============ 自动收集源文件（★ 核心改动 ★） ============
# 递归查找 src/ 下所有 .c 文件
C_SOURCES   = $(shell find src -name '*.c')

# 查找所有汇编文件
ASM_SOURCES = $(shell find . -name '*.s')

# ============ 自动收集头文件路径 ============
# 递归查找所有包含 .h 文件的目录
INCLUDES = -ICMSIS $(addprefix -I, $(sort $(dir $(shell find inc -name '*.h'))))

# ============ 编译选项 ============
CFLAGS  = $(MCU) -D$(DEVICE) $(INCLUDES) -Wall -fdata-sections -ffunction-sections -Os -MMD -MP
LDFLAGS = $(MCU) -T STM32F103C8Tx_FLASH.ld -Wl,--gc-sections -specs=nosys.specs -lm

# ============ 自动构建目标文件列表 ============
# 把 src/drivers/gpio.c → build/gpio.o
C_OBJECTS   = $(addprefix $(BUILD)/, $(notdir $(C_SOURCES:.c=.o)))
ASM_OBJECTS = $(addprefix $(BUILD)/, $(notdir $(ASM_SOURCES:.s=.o)))
OBJECTS     = $(C_OBJECTS) $(ASM_OBJECTS)

# ============ VPATH：告诉 make 去哪里找源文件 ============
VPATH = $(sort $(dir $(C_SOURCES))) $(sort $(dir $(ASM_SOURCES)))

# ============ 构建规则 ============
$(BUILD)/$(TARGET).elf: $(OBJECTS)
	$(CC) $(LDFLAGS) $^ -o $@
	$(SIZE) $@

$(BUILD)/%.o: %.c | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD)/%.o: %.s | $(BUILD)
	$(AS) $(MCU) -c $< -o $@

$(BUILD):
	mkdir -p $(BUILD)

clean:
	$(RM) $(BUILD)

flash: $(BUILD)/$(TARGET).elf
	openocd -f interface/stlink.cfg -f target/stm32f1x.cfg \
		-c "program $< verify reset exit"

debug: $(BUILD)/$(TARGET).elf
	openocd -f interface/stlink.cfg -f target/stm32f1x.cfg &
	$(PREFIX)gdb $< -ex "target remote :3333" -ex "monitor reset halt"

# ============ 自动依赖（-MMD -MP 生成的 .d 文件） ============
-include $(OBJECTS:.o=.d)

.PHONY: clean flash debug
```

### 这版 Makefile 的三个核心技巧

```
技巧①: $(shell find src -name '*.c')
         │
         └─ 自动递归找所有 .c 文件
            新增文件不需要改 Makefile

技巧②: VPATH = $(sort $(dir $(C_SOURCES)))
         │
         └─ 告诉 make："去这些目录里找源文件"
            这样构建规则只需要写 %.o: %.c
            不用为每个子目录写一条规则

技巧③: -MMD -MP
         │
         └─ 编译时自动生成 .d 依赖文件
            当你修改 gpio.h 时，make 会自动重编
            所有 #include "gpio.h" 的 .c 文件
```

### 各场景改动对照表

```
┌──────────────────────┬───────────────┬───────────────────┬────────────────┐
│       场景            │  旧 Makefile   │  新 Makefile(自动) │  需要改什么      │
├──────────────────────┼───────────────┼───────────────────┼────────────────┤
│ src/ 下新增 .c 文件   │  改 C_SOURCES  │  不用改 ✓          │  无             │
│                      │  加一行路径     │                   │                │
├──────────────────────┼───────────────┼───────────────────┼────────────────┤
│ 新增子目录 src/drivers│  改 C_SOURCES  │  不用改 ✓          │  无             │
│                      │  + 新增构建规则 │                   │                │
├──────────────────────┼───────────────┼───────────────────┼────────────────┤
│ 新增头文件目录 inc/xxx│  改 INCLUDES   │  不用改 ✓          │  无             │
├──────────────────────┼───────────────┼───────────────────┼────────────────┤
│ 切换芯片型号          │  改 DEVICE     │  改 DEVICE         │  DEVICE, MCU   │
│ (F103→F407)          │  改 MCU        │  改 MCU            │  链接脚本       │
│                      │  改链接脚本     │  改链接脚本         │  启动文件       │
├──────────────────────┼───────────────┼───────────────────┼────────────────┤
│ 改目标文件名          │  改 TARGET     │  改 TARGET         │  TARGET        │
├──────────────────────┼───────────────┼───────────────────┼────────────────┤
│ 添加外部库(如FatFs)   │  改 C_SOURCES  │  不用改            │  可能加 LDFLAGS │
│                      │  改 INCLUDES   │  不用改            │                │
└──────────────────────┴───────────────┴───────────────────┴────────────────┘
```

### 最终建议

```
项目 < 5 个 .c 文件  →  手写 C_SOURCES 就够了，简单直观
项目 > 5 个 .c 文件  →  切换到自动收集版本，一劳永逸
切换芯片              →  两种都要改 DEVICE/MCU/链接脚本/启动文件
```

自动版本的 Makefile 初始写起来稍复杂，但只要写一次，后续开发中**永远不需要再碰它**。

## 注意事项 & 踩坑

- Makefile 命令必须用 TAB 缩进，不能用空格
- 变量赋值时 `=` 是递归展开，`:=` 是立即展开
- `-O0` 是字母 O 加数字 0，不是两个零
- 首次编译前确保 `build/` 目录不存在，否则可能残留旧文件

## 相关笔记

- [[STM32寄存器开发概述]]
- [[STM32寄存器开发构建过程详解]]
- [[STM32调试指南]]

## 参考来源

- GNU Make 官方文档
- ARM GCC 编译器手册
