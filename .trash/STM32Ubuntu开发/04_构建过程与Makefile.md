## 笔记 4：构建过程与 Makefile

> **覆盖原笔记**：`Makefile基础与进阶`、`AS变量拆解`、`STM32寄存器开发构建过程详解`

### 4.1 构建流程总览

```
  main.c + stm32f10x.h
         │
    ┌────▼────┐
    │ 预处理器  │  -E     展开 #include、宏替换 → main.i
    └────┬────┘
    ┌────▼────┐
    │  编译器   │  -S     C → ARM 汇编 → main.s
    └────┬────┘
    ┌────▼────┐
    │  汇编器   │  -c     汇编 → 机器码 → main.o (ELF)
    └────┬────┘
    ┌────▼────┐
    │  链接器   │  -T .ld 合并 .o，分配地址 → firmware.elf
    └────┬────┘
    ┌────▼────┐
    │ objcopy  │         去元数据 → firmware.bin / firmware.hex
    └────┬────┘
         ▼
     烧录到芯片 Flash
```

### 4.2 完整 Makefile（自动收集源文件版）

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

### 4.3 关键语法速查

#### AS 变量详解

```makefile
AS = $(PREFIX)gcc -x assembler-with-cpp
```

| 部分 | 含义 |
|------|------|
| `$(PREFIX)gcc` | 展开为 `arm-none-eabi-gcc`，用 gcc 驱动汇编 |
| `-x assembler-with-cpp` | 强制按"带预处理的汇编"处理输入 |

选择 `assembler-with-cpp` 而非直接用 `as`，是为了让 `.S` 文件中可以使用 `#include`、`#define`、`#ifdef`、宏展开等预处理特性。`.s`（小写）通常不经过预处理器，`.S`（大写）需要。

#### CFLAGS 参数

| 参数 | 作用 |
|------|------|
| `-mcpu=cortex-m3 -mthumb` | 目标 CPU 和指令集 |
| `-DSTM32F103xB` | 定义预处理宏 |
| `-fdata-sections -ffunction-sections` | 每个变量/函数独立 Section，配合 `--gc-sections` 删除未使用代码 |
| `-Os` | 体积优化（嵌入式首选）；调试时用 `-O0 -g` |
| `-MMD -MP` | 自动生成 `.d` 依赖文件，改头文件时自动重编 |

#### LDFLAGS 参数

| 参数 | 作用 |
|------|------|
| `-T xxx.ld` | 链接脚本，定义 Flash/RAM 布局 |
| `-Wl,--gc-sections` | 删除未被引用的 Section |
| `-specs=nosys.specs` | 裸机环境，提供系统调用桩函数 |
| `-lm` | 链接数学库 |

#### Makefile 核心语法

| 语法 | 含义 | 示例 |
|------|------|------|
| `$@` | 目标文件名 | `build/firmware.elf` |
| `$^` | 所有依赖 | `build/main.o build/gpio.o` |
| `$<` | 第一个依赖 | `build/main.o` |
| `%.o: %.c` | 模式规则（通配符） | 一条规则覆盖所有 `.c` |
| `VPATH` | 源文件搜索路径 | 解决子目录源文件查找 |
| `| $(BUILD)` | 顺序依赖 | 目录存在即可，时间戳变化不触发重编 |
| `.PHONY` | 伪目标声明 | `clean`、`flash` 等不是文件名 |
| `$(shell ...)` | 执行 shell 命令 | `$(shell find src -name '*.c')` |
| `$(var:.c=.o)` | 后缀替换 | `src/main.c` → `src/main.o` |
| `$(notdir ...)` | 去掉目录前缀 | `src/drivers/gpio.o` → `gpio.o` |
| `$(addprefix ...)` | 添加前缀 | `gpio.o` → `build/gpio.o` |
| `$(sort ...)` | 排序 + 去重 | 用于 VPATH 去重 |
| `-include` | 包含文件，不存在不报错 | 包含 `.d` 依赖文件 |

### 4.4 Makefile 设计决策总结

| 设计 | 解决的问题 |
|------|-----------|
| 变量 (`CC`, `CFLAGS`) | 一处定义，处处生效 |
| 依赖关系 | 只编译变了的文件（增量编译） |
| 模式规则 (`%`) | N 条相同规则压缩为 1 条 |
| `$(shell find)` | 新增 `.c` 文件无需改 Makefile |
| `VPATH` | 子目录不影响编译规则 |
| `-MMD -MP` | 改头文件自动触发重编 |
| 顺序依赖 `\|` | 目录时间戳变化不触发重编 |
| `--gc-sections` | 删除死代码，省 Flash |
| `.PHONY` | 避免文件名冲突 |

### 4.5 增量改动指南

| 场景 | 需要改什么 |
|------|-----------|
| `src/` 下新增 `.c` 文件 | **不用改**（自动收集） |
| 新增子目录 `src/drivers/` | **不用改** |
| 新增头文件目录 `inc/xxx/` | **不用改** |
| 切换芯片 (F103→F407) | 改 `DEVICE`、`MCU`、链接脚本、启动文件 |
| 改目标文件名 | 改 `TARGET` |
| 调试模式 | 将 `-Os` 改为 `-O0 -g` |

---