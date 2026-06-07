# STM32 Ubuntu 开发

> **来源清单**（已提炼）：
> - [x] 01_开发环境搭建
> - [x] 02_STM32CubeMX安装
> - [x] 03_项目结构与支持文件
> - [x] 04_构建过程与Makefile
> - [x] 05_调试完整指南
> - [x] 06_速查手册
>
> **更新时间**：2026-06-07

## 一、开发环境搭建

### 工具链组成

完整的STM32开发工具链包含四个核心组件：

- **编辑器**：VS Code、Vim/NeoVim等
- **交叉编译工具链**：`arm-none-eabi-gcc`、`arm-none-eabi-gdb`（Ubuntu 24.04起由`gdb-multiarch`替代）
- **烧录工具**：OpenOCD、st-flash
- **调试器**：gdb-multiarch
- **调试探针**：ST-Link、J-Link、DAP-Link

### 安装交叉编译工具链

```bash
sudo apt update

# 编译器 + 二进制工具
sudo apt install -y gcc-arm-none-eabi binutils-arm-none-eabi

# 调试器（Ubuntu 24.04起arm-none-eabi-gdb已被gdb-multiarch替代）
sudo apt install -y gdb-multiarch

# 构建工具
sudo apt install -y build-essential cmake make

# 串口工具
sudo apt install -y minicom screen

# Python（用于OpenOCD辅助脚本等）
sudo apt install -y python3 python3-pip python3-venv
```

**验证安装**：
```bash
arm-none-eabi-gcc --version
gdb-multiarch --version
```

**Ubuntu 24.04重要说明**：`arm-none-eabi-gdb`包已移除，`gdb-multiarch`功能完全等价，可直接替代。如某些脚本硬编码了`arm-none-eabi-gdb`，需从ARM官方下载完整工具链手动安装到`/opt/toolchains/`。

### 安装ST-Link工具与OpenOCD

```bash
sudo apt install -y stlink-tools stlink-gui openocd
st-info --version
openocd --version
```

### 配置udev规则（非root烧录）

创建文件`/etc/udev/rules.d/49-stlinkv2.rules`：

```
# ST-Link V2
SUBSYSTEMS=="usb", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="3748", MODE="0666", GROUP="plugdev"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="374b", MODE="0666", GROUP="plugdev"
# ST-Link V2-1
SUBSYSTEMS=="usb", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="374d", MODE="0666", GROUP="plugdev"
# ST-Link V3
SUBSYSTEMS=="usb", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="374e", MODE="0666", GROUP="plugdev"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="374f", MODE="0666", GROUP="plugdev"
```

应用规则：
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
sudo usermod -a -G plugdev $USER
# 重新登录使组权限生效
```

**测试连接**：
```bash
lsusb | grep -i stlink
st-info --probe
```

### 环境变量（可选）

```bash
echo 'export PATH=$PATH:/usr/bin/arm-none-eabi/bin' >> ~/.bashrc
echo 'export ARM_TOOLCHAIN_PATH=/usr/bin/arm-none-eabi' >> ~/.bashrc
source ~/.bashrc
```

### VS Code插件配置

| 插件 | 用途 |
|------|------|
| Cortex-Debug | ARM调试核心插件 |
| C/C++ | IntelliSense、调试支持 |
| Cortex-Debug: Device Support Pack - STM32F1 | SVD寄存器可视化（可选） |

在`launch.json`中将`gdbPath`设为`gdb-multiarch`：

```json
{
    "version": "0.2.0",
    "configurations": [{
        "name": "STM32 Debug",
        "type": "cortex-debug",
        "request": "launch",
        "servertype": "openocd",
        "executable": "${workspaceFolder}/build/firmware.elf",
        "configFiles": ["interface/stlink.cfg", "target/stm32f1x.cfg"],
        "gdbPath": "gdb-multiarch",
        "device": "STM32F103C8",
        "svdFile": "${workspaceFolder}/STM32F103xx.svd",
        "runToEntryPoint": "main",
        "preLaunchTask": "build"
    }]
}
```

📄 [原文01: 开发环境搭建](../raw/嵌入式开发/STM32Ubuntu开发/01_开发环境搭建.md)

## 二、STM32CubeMX安装

### 推荐安装方法：Flatpak

```bash
sudo apt install -y flatpak default-jre
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install -y flathub com.st.STM32CubeMX
```

**验证安装**：
```bash
flatpak list | grep -i stm32
# STM32CubeMX   com.st.STM32CubeMX   6.17.0   stable   system
```

**启动**：`flatpak run com.st.STM32CubeMX`

### 更新与卸载

```bash
flatpak update com.st.STM32CubeMX        # 更新
flatpak uninstall --delete-data com.st.STM32CubeMX  # 卸载
```

### 首次使用配置

1. 启动后下载MCU数据库（需联网）
2. Help → Manage embedded software packages → 安装STM32F1系列固件包
3. 新建项目时选择Makefile作为Toolchain，可直接导出寄存器级项目骨架

📄 [原文02: STM32CubeMX安装](../raw/嵌入式开发/STM32Ubuntu开发/02_STM32CubeMX安装.md)

## 三、项目结构与支持文件

### 推荐目录结构

```
project/
├── Makefile
├── linker/
│   └── STM32F103C8Tx_FLASH.ld
├── startup/
│   └── startup_stm32f103xb.s
├── cmsis/
│   ├── core_cm3.h
│   └── cmsis_gcc.h
├── system/
│   ├── stm32f10x.h              # 寄存器结构体定义
│   ├── system_stm32f10x.c       # SystemInit()实现
│   └── system_stm32f10x.h
├── app/
│   ├── main.c
│   └── inc/
│       └── main.h
├── build/                        # 自动生成
└── output/                       # 自动生成
```

### 获取支持文件

所有文件来自**STM32CubeF1**固件包：

```bash
git clone https://github.com/STMicroelectronics/STM32CubeF1.git
```

| 文件 | 固件包内路径 |
|------|-------------|
| `stm32f10x.h` | `Drivers/CMSIS/Device/ST/STM32F1xx/Include/` |
| `system_stm32f10x.c/.h` | `Drivers/CMSIS/Device/ST/STM32F1xx/Source/Templates/`及`Include/` |
| `core_cm3.h` | `Drivers/CMSIS/Include/` |
| 启动文件(GCC) | `Drivers/CMSIS/Device/ST/STM32F1xx/Source/Templates/gcc/startup_stm32f103xb.s` |

**链接脚本**不在固件包中，需手写或从STM32CubeIDE/CubeMX项目导出。

### 链接脚本模板

```ld
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

### 常见STM32F1型号内存配置

| 型号 | Flash | RAM |
|------|-------|-----|
| F103C8T6 | 64K | 20K |
| F103CBT6 | 128K | 20K |
| F103RCT6 | 256K | 48K |
| F103ZET6 | 512K | 64K |

📄 [原文03: 项目结构与支持文件](../raw/嵌入式开发/STM32Ubuntu开发/03_项目结构与支持文件.md)

## 四、构建过程与Makefile

### 构建流程总览

```
  main.c + stm32f10x.h
         │
    ┌────▼────┐
    │ 预处理器  │  -E     展开#include、宏替换 → main.i
    └────┬────┘
    ┌────▼────┐
    │  编译器   │  -S     C → ARM汇编 → main.s
    └────┬────┘
    ┌────▼────┐
    │  汇编器   │  -c     汇编 → 机器码 → main.o (ELF)
    └────┬────┘
    ┌────▼────┐
    │  链接器   │  -T .ld 合并.o，分配地址 → firmware.elf
    └────┬────┘
    ┌────▼────┐
    │ objcopy  │         去元数据 → firmware.bin / firmware.hex
    └────┬────┘
         ▼
     烧录到芯片Flash
```

### 完整Makefile（自动收集源文件版）

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

# ============ 自动收集源文件 ============
C_SOURCES   = $(shell find src -name '*.c')
ASM_SOURCES = $(shell find . -name '*.s')

# ============ 自动收集头文件路径 ============
INCLUDES = -ICMSIS $(addprefix -I, $(sort $(dir $(shell find inc -name '*.h'))))

# ============ 编译选项 ============
CFLAGS  = $(MCU) -D$(DEVICE) $(INCLUDES) -Wall -fdata-sections -ffunction-sections -Os -MMD -MP
LDFLAGS = $(MCU) -T linker/STM32F103C8Tx_FLASH.ld -Wl,--gc-sections -specs=nosys.specs -lm

# ============ 目标文件列表 ============
C_OBJECTS   = $(addprefix $(BUILD)/, $(notdir $(C_SOURCES:.c=.o)))
ASM_OBJECTS = $(addprefix $(BUILD)/, $(notdir $(ASM_SOURCES:.s=.o)))
OBJECTS     = $(C_OBJECTS) $(ASM_OBJECTS)

# ============ VPATH ============
VPATH = $(sort $(dir $(C_SOURCES))) $(sort $(dir $(ASM_SOURCES)))

# ============ 输出文件 ============
ELF = $(BUILD)/$(TARGET).elf
BIN = $(BUILD)/$(TARGET).bin
HEX = $(BUILD)/$(TARGET).hex

# ============ 构建规则 ============
all: $(ELF) $(BIN) $(HEX)
	$(SIZE) $(ELF)

$(ELF): $(OBJECTS)
	$(CC) $(LDFLAGS) $^ -o $@

$(BIN): $(ELF)
	$(OBJCOPY) -O binary $< $@

$(HEX): $(ELF)
	$(OBJCOPY) -O ihex $< $@

$(BUILD)/%.o: %.c | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD)/%.o: %.s | $(BUILD)
	$(AS) $(MCU) -c $< -o $@

$(BUILD):
	mkdir -p $(BUILD)

clean:
	$(RM) $(BUILD)

flash: $(ELF)
	openocd -f interface/stlink.cfg -f target/stm32f1x.cfg \
		-c "program $(HEX) verify reset exit"

debug: $(ELF)
	openocd -f interface/stlink.cfg -f target/stm32f1x.cfg &
	sleep 1
	$(PREFIX)gdb $(ELF) \
		-ex "target remote localhost:3333" \
		-ex "monitor reset halt" \
		-ex "break main" \
		-ex "continue"

-include $(OBJECTS:.o=.d)
.PHONY: all clean flash debug
```

### 关键语法速查

#### AS变量详解

```makefile
AS = $(PREFIX)gcc -x assembler-with-cpp
```

| 部分 | 含义 |
|------|------|
| `$(PREFIX)gcc` | 展开为`arm-none-eabi-gcc`，用gcc驱动汇编 |
| `-x assembler-with-cpp` | 强制按"带预处理的汇编"处理输入 |

选择`assembler-with-cpp`而非直接用`as`，是为了让`.S`文件中可以使用`#include`、`#define`、`#ifdef`、宏展开等预处理特性。`.s`（小写）通常不经过预处理器，`.S`（大写）需要。

#### CFLAGS参数

| 参数 | 作用 |
|------|------|
| `-mcpu=cortex-m3 -mthumb` | 目标CPU和指令集 |
| `-DSTM32F103xB` | 定义预处理宏 |
| `-fdata-sections -ffunction-sections` | 每个变量/函数独立Section，配合`--gc-sections`删除未使用代码 |
| `-Os` | 体积优化（嵌入式首选）；调试时用`-O0 -g` |
| `-MMD -MP` | 自动生成`.d`依赖文件，改头文件时自动重编 |

#### LDFLAGS参数

| 参数 | 作用 |
|------|------|
| `-T xxx.ld` | 链接脚本，定义Flash/RAM布局 |
| `-Wl,--gc-sections` | 删除未被引用的Section |
| `-specs=nosys.specs` | 裸机环境，提供系统调用桩函数 |
| `-lm` | 链接数学库 |

#### Makefile核心语法

| 语法 | 含义 | 示例 |
|------|------|------|
| `$@` | 目标文件名 | `build/firmware.elf` |
| `$^` | 所有依赖 | `build/main.o build/gpio.o` |
| `$<` | 第一个依赖 | `build/main.o` |
| `%.o: %.c` | 模式规则（通配符） | 一条规则覆盖所有`.c` |
| `VPATH` | 源文件搜索路径 | 解决子目录源文件查找 |
| `\| $(BUILD)` | 顺序依赖 | 目录存在即可，时间戳变化不触发重编 |
| `.PHONY` | 伪目标声明 | `clean`、`flash`等不是文件名 |
| `$(shell ...)` | 执行shell命令 | `$(shell find src -name '*.c')` |
| `$(var:.c=.o)` | 后缀替换 | `src/main.c` → `src/main.o` |
| `$(notdir ...)` | 去掉目录前缀 | `src/drivers/gpio.o` → `gpio.o` |
| `$(addprefix ...)` | 添加前缀 | `gpio.o` → `build/gpio.o` |
| `$(sort ...)` | 排序+去重 | 用于VPATH去重 |
| `-include` | 包含文件，不存在不报错 | 包含`.d`依赖文件 |

### Makefile设计决策总结

| 设计 | 解决的问题 |
|------|-----------|
| 变量 (`CC`, `CFLAGS`) | 一处定义，处处生效 |
| 依赖关系 | 只编译变了的文件（增量编译） |
| 模式规则 (`%`) | N条相同规则压缩为1条 |
| `$(shell find)` | 新增`.c`文件无需改Makefile |
| `VPATH` | 子目录不影响编译规则 |
| `-MMD -MP` | 改头文件自动触发重编 |
| 顺序依赖 `\|` | 目录时间戳变化不触发重编 |
| `--gc-sections` | 删除死代码，省Flash |
| `.PHONY` | 避免文件名冲突 |

### 增量改动指南

| 场景 | 需要改什么 |
|------|-----------|
| `src/`下新增`.c`文件 | **不用改**（自动收集） |
| 新增子目录`src/drivers/` | **不用改** |
| 新增头文件目录`inc/xxx/` | **不用改** |
| 切换芯片 (F103→F407) | 改`DEVICE`、`MCU`、链接脚本、启动文件 |
| 改目标文件名 | 改`TARGET` |
| 调试模式 | 将`-Os`改为`-O0 -g` |

📄 [原文04: 构建过程与Makefile](../raw/嵌入式开发/STM32Ubuntu开发/04_构建过程与Makefile.md)

## 五、调试完整指南

### 调试架构

```
你的电脑                                    STM32芯片
┌───────────────────────────────────┐      ┌──────────────────┐
│  GDB (gdb-multiarch)              │      │  CPU + 调试硬件    │
│       │  TCP :3333                │      │  ├── 6个硬件断点    │
│       ▼                           │      │  ├── 4个硬件观察点  │
│  OpenOCD (GDB Server)             │      │  └── DWT周期计数器│
│       │  USB                      │      │                  │
│       ▼                           │      │                  │
│  ST-Link  ══════SWD══════════════════════SWD接口             │
│  (SWDIO + SWDCK)                  │      │                  │
└───────────────────────────────────┘      └──────────────────┘
```

### 启动调试

```bash
# 终端1：启动OpenOCD
openocd -f interface/stlink.cfg -f target/stm32f1x.cfg
# 成功输出：Listening on port 3333 for gdb connections

# 终端2：启动GDB
gdb-multiarch build/firmware.elf
```

### GDB核心命令

#### 连接与控制

| 命令 | 缩写 | 功能 |
|------|------|------|
| `target remote localhost:3333` | | 连接OpenOCD |
| `monitor reset halt` | | 复位并暂停CPU |
| `monitor reset init` | | 复位并初始化 |
| `monitor reset run` | | 复位并运行 |
| `load` | | 下载固件到Flash |
| `continue` | `c` | 继续运行到下一断点 |
| `Ctrl+C` | | 手动暂停 |
| `quit` | `q` | 退出GDB |

#### 断点

```gdb
break main                    # 函数入口
break main.c:18               # 文件:行号
break *0x08000100             # 绝对地址
break main.c:22 if counter==10 # 条件断点
tbreak main                   # 临时断点（只停一次）
hbreak *0x08000100            # 强制硬件断点
info breakpoints              # 列出所有断点
delete 3                      # 删除3号断点
delete                        # 删除所有断点
```

Cortex-M3通常有**6个硬件断点**，用完需删除才能新建。

#### 单步执行

| 命令 | 缩写 | 功能 |
|------|------|------|
| `step` | `s` | 单步（进入函数） |
| `next` | `n` | 单步（跳过函数） |
| `stepi` | `si` | 单步汇编指令（进入） |
| `nexti` | `ni` | 单步汇编指令（跳过） |
| `finish` | `fin` | 执行到当前函数返回 |
| `until` | `u` | 执行到循环结束或指定行 |

#### 观察点（硬件，通常4个）

```gdb
watch *(unsigned int*)0x4001100C    # 写观察点
rwatch *(unsigned int*)0x4001100C   # 读观察点
awatch *(unsigned int*)0x4001100C   # 读写观察点
watch *$odr if (*$odr & 0x2000)!=0  # 条件观察点
info watchpoints
```

当被监测地址被修改时，GDB自动停下并显示旧值和新值。

#### 查看数据

```gdb
# CPU寄存器
info registers
print/x $pc
print/x $sp
print/x $psr

# 外设寄存器（内存映射I/O）
x /xw 0x4001100C              # GPIOC_ODR，十六进制32位
x /tw 0x40011004              # GPIOC_CRH，二进制
x /4xw 0x40021018             # RCC起始，连续4个字
x /i $pc                      # 当前指令

# 格式：x /NFS 地址
# N=数量, F=格式(x十六进制/d十进制/t二进制/c字符/s字符串), S=大小(b字节/h半字/w字)

# 变量
print my_variable
print /x my_variable          # 十六进制
print /t my_variable          # 二进制
print RCC->APB2ENR            # 直接读外设寄存器
info locals                   # 所有局部变量
display my_variable           # 每次暂停自动显示

# GDB便捷变量
set $RCC_APB2ENR = (unsigned int*)0x40021018
x /xw $RCC_APB2ENR
```

#### 修改状态

```gdb
set my_variable = 100
set *(unsigned int*)0x4001100C = 0x2000   # 写外设寄存器
set $r0 = 0x55
set $pc = 0x08000100                       # 修改PC（慎用）
return 42                                  # 跳过函数执行，直接返回值
```

#### 调用栈与反汇编

```gdb
backtrace                   # 或bt，调用栈
bt full                     # 含局部变量
frame 1                     # 切换栈帧
up / down                   # 上/下移动栈帧
info frame                  # 栈帧详情

disassemble main            # 反汇编整个函数
disassemble /m main         # 混合源码和汇编
disassemble /r main         # 显示机器码
```

#### TUI文本界面

```gdb
layout src                  # 源码视图
layout asm                  # 汇编视图
layout split                # 源码+汇编
layout regs                 # 寄存器窗口
focus cmd/src/asm           # 切换焦点
Ctrl+X, A                   # 退出TUI
```

#### 自定义命令与脚本

```gdb
# 定义便捷变量
set $GPIOC_ODR = (unsigned int*)0x4001100C

# 定义宏
define reload
  monitor reset halt
  load
  monitor reset init
end

# 启动脚本
# gdb-multiarch -x script.gdb firmware.elf
# script.gdb内容：
#   target remote localhost:3333
#   monitor reset halt
#   load
#   break main
#   continue
```

### 调试编译选项

```makefile
# 调试版（开发时）
CFLAGS = $(MCU) -D$(DEVICE) $(INCLUDES) -Wall -fdata-sections -ffunction-sections -g -O0

# 发布版（烧给客户）
CFLAGS = $(MCU) -D$(DEVICE) $(INCLUDES) -Wall -fdata-sections -ffunction-sections -Os
```

| 选项 | 效果 |
|------|------|
| `-g` | 生成调试信息（符号表、行号映射） |
| `-O0` | 关闭优化，变量值不会被优化掉，断点不会乱跳 |
| `-Os` | 体积优化，不带调试信息 |

### OpenOCD telnet调试

```bash
telnet localhost 4444
```

```
> halt                      # 暂停CPU
> reg                       # 显示内核寄存器
> mdw 0x4001100C            # 读外设寄存器（32位）
> mww 0x4001100C 0x2000     # 写外设寄存器
> resume                    # 恢复运行
> reset halt                # 复位并暂停
> bp                        # 列出硬件断点
```

### SVD文件（寄存器可视化）

```bash
wget https://raw.githubusercontent.com/posborne/cmsis-svd/master/data/STMicro/STM32F103xx.svd
```

在`launch.json`中配置`"svdFile": "${workspaceFolder}/STM32F103xx.svd"`，调试时可在VS Code侧边栏**Cortex Peripherals**面板中直接展开查看每个外设寄存器的每一位。

### 常见调试场景

#### 场景1：确认时钟使能

```gdb
(gdb) x /xw 0x40021018                # RCC_APB2ENR
(gdb) print /t (*(unsigned int*)0x40021018)  # 二进制，检查bit4
```

#### 场景2：监测GPIO翻转

```gdb
(gdb) watch *(unsigned int*)0x4001100C  # GPIOC_ODR
(gdb) continue
# 每次修改ODR自动停下，显示新旧值
```

#### 场景3：追踪HardFault

```gdb
(gdb) bt full
(gdb) frame 0
(gdb) print/x $pc                      # 异常地址
(gdb) print/x $lr                      # EXC_RETURN
(gdb) disassemble $pc-8, $pc+8
```

#### 场景4：测量函数执行时间

```gdb
(gdb) monitor mdw 0xE0001004           # DWT周期计数器
(gdb) continue                         # 执行到函数后断点
(gdb) monitor mdw 0xE0001004           # 再读
# 差值 / 时钟频率 = 执行时间
```

### 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `Error: init mode failed` | 接线或配置错误 | 检查SWD接线，尝试`reset_config srst_only srst_nogate` |
| 无法连接`:3333` | OpenOCD未启动或端口占用 | 确认OpenOCD运行中，`netstat -tlnp \| grep 3333` |
| 变量显示`<optimized out>` | 编译时用了优化 | 改为`-O0 -g`重新编译 |
| 断点设置失败 | 硬件断点用完（6个） | 删除不用的断点`delete <编号>` |
| `load`失败 | Flash写保护 | OpenOCD控制台执行`flash erase_sector 0 0 0` |
| 程序下载后不运行 | 未复位 | 执行`monitor reset init` |

📄 [原文05: 调试完整指南](../raw/嵌入式开发/STM32Ubuntu开发/05_调试完整指南.md)

## 六、速查手册

### 工具链验证

```bash
arm-none-eabi-gcc --version
gdb-multiarch --version
openocd --version
st-info --probe
```

### 常用Make命令

```bash
make                    # 编译
make clean              # 清理
make flash              # 烧录
make debug              # 启动调试
```

### GDB命令速查

| 目的 | 命令 |
|------|------|
| 连接 | `target remote localhost:3333` |
| 暂停 | `Ctrl+C`或`monitor halt` |
| 继续 | `continue` |
| 单步（源码） | `step`/`next` |
| 单步（汇编） | `stepi`/`nexti` |
| 断点 | `break 位置` |
| 条件断点 | `break 位置 if 条件` |
| 观察点 | `watch 表达式` |
| 查看断点 | `info breakpoints` |
| 查看寄存器 | `info registers`/`print $r0` |
| 查看内存 | `x /格式 地址` |
| 修改 | `set 变量=值` |
| 调用栈 | `backtrace` |
| 反汇编 | `disassemble` |
| 源码 | `list` |
| TUI | `layout split`/`Ctrl+X A` |
| 下载 | `load` |
| 复位 | `monitor reset init` |
| 帮助 | `help 命令名` |

### 硬件资源限制

| 资源 | 数量 | 说明 |
|------|------|------|
| 硬件断点 | 6 | FPB提供，Flash中必须用硬件断点 |
| 硬件观察点 | 4 | DWT提供，可监测内存地址读写 |
| DWT周期计数器 | 1 | 地址`0xE0001004`，用于测量执行时间 |

### 内存布局速查

```
Flash (0x0800_0000)          RAM (0x2000_0000)
┌──────────────────┐         ┌──────────────────┐
│ .isr_vector       │         │ .data（从Flash拷贝）│
│ .text（代码）      │         │ .bss（启动清零）    │
│ .rodata（常量）    │         │ 堆↓              │
│ .data 初始值 ───拷贝──→     │ ↑栈              │
└──────────────────┘         └──────────────────┘
```

📄 [原文06: 速查手册](../raw/嵌入式开发/STM32Ubuntu开发/06_速查手册.md)