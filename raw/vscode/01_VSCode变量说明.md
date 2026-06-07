概述

`${ExecutableName}` 是 VSCode 中代表"当前可执行文件名称（不含扩展名）"的变量，常用于嵌入式项目中生成同名的 `.hex` 固件文件。

## 核心内容

### ${ExecutableName} — 可执行文件的名称

这是一个**变量 / 占位符**，代表"当前要生成/调试的可执行文件的名字（不含扩展名）"。

VSCode 本身**没有**名为 `ExecutableName` 的预定义变量，它可能来自以下几个地方：

- **自定义输入变量**（最常见）— 在 `tasks.json` 里通过 `inputs` 自定义，比如弹框让你输入项目名：

```json
"inputs": [
  {
    "id": "ExecutableName",
    "type": "promptString",
    "description": "输入可执行文件名"
  }
]
```

在命令中引用时要用 `${input:ExecutableName}`，但有些模板可能直接写成 `${ExecutableName}`（需插件支持）。

- **环境变量** — 如果系统或终端里设置了 `ExecutableName` 这个环境变量，可以写成 `${env:ExecutableName}`

- **某个扩展注入的变量** — 例如 **CMake Tools**、**PlatformIO** 等嵌入式/构建扩展，可能会在上下文中提供类似 `${cmake.buildTargetName}` 或 `${platformio.env}` 这种变量

- **Shell / Makefile 里的变量** — 如果任务直接执行一段 Shell 命令，`${ExecutableName}` 可能是 Makefile 或脚本里自己定义的变量，运行时由 Shell 替换

### .hex — Intel HEX 格式固件文件

**.hex 文件**是嵌入式开发里非常常见的**固件烧录文件**，全称 Intel HEX。它把编译生成的机器码（二进制）用 ASCII 十六进制文本表示，并带有地址信息，方便烧录器/调试器（如 J-Link、ST-Link、OpenOCD）写入单片机。

### 合起来的含义

**`${ExecutableName}.hex`** 就表示：一个和可执行文件同名的 HEX 固件文件。

例如，如果最终要生成的程序名叫 `blinky`，运行时就会被解析成 `blinky.hex`。

典型使用场景：嵌入式 C/C++ 项目里，先编译出 `blinky.elf`，再通过 `objcopy` 转换为 `blinky.hex`，以便烧录。

```bash
arm-none-eabi-objcopy -O ihex ${ExecutableName}.elf ${ExecutableName}.hex
```

### 更推荐的替代方案

可以直接利用 VSCode 的内置变量，不必自己另造一个 `ExecutableName`。

例如用 `${fileBasenameNoExtension}`，它自动取当前文件的文件名（不含扩展名），非常适合单文件项目：

```json
"command": "arm-none-eabi-objcopy -O ihex ${fileBasenameNoExtension}.elf ${fileBasenameNoExtension}.hex"
```

#### 嵌入式项目常用内置变量

| 变量 | 示例值 | 说明 |
|---|---|---|
| `${fileBasenameNoExtension}` | `main` | 当前文件名，不含扩展名 |
| `${workspaceFolder}` | `/home/user/stm32-project` | 工作区根目录 |
| `${file}` | `/home/user/stm32-project/main.c` | 当前文件完整路径 |
| `${fileDirname}` | `/home/user/stm32-project` | 当前文件所在目录 |
| `${fileBasename}` | `main.c` | 当前文件名，含扩展名 |
| `${input:ExecutableName}` | 用户输入值 | 自定义 promptString 输入 |

