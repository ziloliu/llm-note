# FSMC 控制器

> **来源清单**（已提炼）：
> - [x] 01_FSMC概述与基本原理
> - [x] 02_外部设备地址映射
> - [x] 03_LCD寻址与命令数据写入
> - [x] 04_NOR Flash与PSRAM读写时序
> - [x] 05_IS62WV51216 SRAM芯片详解
> - [x] 06_IS62WV51216时序参数详解
> - [x] 07_IS62WV51216与FSMC模式1配置
> - [x] 08_硬件电路设计与寄存器配置
> - [x] 09_FSMC扩展外部SRAM寄存器方式
> - [x] 10_综合复习与地址映射深入解析
> - [x] 11_HAL库调用方式
>
> **更新时间**：2026-09-15

---

## 一、FSMC 概述

### 1.1 什么是 FSMC

FSMC（Flexible Static Memory Controller，灵活的静态存储器控制器）是 STM32 内部的一个外设模块，用于连接外部存储器。

**核心作用**：
- 将 CPU 发出的内部总线访问，自动转换为外部存储器所需的时序协议
- 支持多种外部存储器类型：NOR Flash、PSRAM、SRAM、NAND Flash、PC Card
- 配置完成后，CPU 可以像访问内部内存一样直接读写外部存储器

**工作原理**：
```
CPU / DMA  ←→  AHB 总线  ←→  FSMC  ←→  外部存储器
                        （中间代理人）
```

📄 [原文01: FSMC概述与基本原理](../raw/嵌入式开发/FSMC控制器/01_FSMC概述与基本原理.md)

### 1.2 为什么需要 FSMC

**片内存储资源的局限**：
- STM32F103 片内 SRAM：64 KB
- STM32F103 片内 Flash：512 KB
- 对于大量数据处理场景远远不够

**典型资源不足的场景**：
- 图像处理（高分辨率液晶屏显示）
- 大数组、复杂算法
- 需要更多运行内存的应用

**解决方案**：
- 使用 FSMC 连接外部 SRAM 芯片，扩展运行内存
- CPU 通过 FSMC 像访问片内内存一样访问外部 SRAM

📄 [原文01: FSMC概述与基本原理](../raw/嵌入式开发/FSMC控制器/01_FSMC概述与基本原理.md)

### 1.3 FSMC 与传统扩展方式的对比

| 对比项 | 传统方式（I²C/SPI） | FSMC 方式 |
|--------|-------------------|-----------|
| 接口类型 | 串行接口 | 并行接口（地址线+数据线） |
| 速度 | 较慢 | 快（总线速度） |
| 复杂度 | 需要编写通信函数 | 配置后直接内存访问 |
| 地址空间 | 需要手动管理 | 统一地址映射 |
| 适用场景 | 小容量存储 | 大容量存储、需要高速访问 |

📄 [原文01: FSMC概述与基本原理](../raw/嵌入式开发/FSMC控制器/01_FSMC概述与基本原理.md)

---

## 二、FSMC 地址空间

### 2.1 FSMC 管理的地址范围

FSMC 管理的地址空间位于存储器映射的 Block 3 和 Block 4：
- Block 3：0x6000_0000 ~ 0x7FFF_FFFF（512 MB）
- Block 4：0x8000_0000 ~ 0x9FFF_FFFF（512 MB）
- FSMC 总共可管理的地址空间 = 512 MB + 512 MB = 1 GB

📄 [原文02: 外部设备地址映射](../raw/嵌入式开发/FSMC控制器/02_外部设备地址映射.md)

### 2.2 四个 Bank 的划分

1 GB 地址空间划分为 4 个 Bank（区），每个 Bank 256 MB：

| Bank | 地址范围 | 大小 | 支持的存储器类型 |
|------|----------|------|-----------------|
| Bank 1 | 0x6000_0000 ~ 0x6FFF_FFFF | 256 MB | NOR Flash / PSRAM / SRAM |
| Bank 2 | 0x7000_0000 ~ 0x7FFF_FFFF | 256 MB | NAND Flash |
| Bank 3 | 0x8000_0000 ~ 0x8FFF_FFFF | 256 MB | NAND Flash |
| Bank 4 | 0x9000_0000 ~ 0x9FFF_FFFF | 256 MB | PC Card |

**关键点**：不同类型的外部存储器映射到不同的 Bank，不能混用。

📄 [原文02: 外部设备地址映射](../raw/嵌入式开发/FSMC控制器/02_外部设备地址映射.md)

### 2.3 Bank 1 的子区划分

Bank 1（256 MB）进一步划分为 4 个子区，每个子区 64 MB，通过片选信号 NE1~NE4 选择：

| 子区 | 地址范围 | 片选信号 | 大小 |
|------|----------|----------|------|
| Bank1-1 | 0x6000_0000 ~ 0x63FF_FFFF | NE1 | 64 MB |
| Bank1-2 | 0x6400_0000 ~ 0x67FF_FFFF | NE2 | 64 MB |
| Bank1-3 | 0x6800_0000 ~ 0x6BFF_FFFF | NE3 | 64 MB |
| Bank1-4 | 0x6C00_0000 ~ 0x6FFF_FFFF | NE4 | 64 MB |

**使用方式**：外部存储器的片选引脚连接到 STM32 的 NE1~NE4 引脚，确定其在 Bank 1 中的具体地址。

📄 [原文02: 外部设备地址映射](../raw/嵌入式开发/FSMC控制器/02_外部设备地址映射.md)

---

## 三、LCD 寻址与命令/数据写入

### 3.1 LCD 显存的存储器类型

LCD 的 GRAM（显存）在 FSMC 中定义为 SRAM 类型：
- GRAM 不是 ROM（不是只读的）
- GRAM 不是 Flash（不需要擦除后写入）
- GRAM 可以随机读写（任意地址直接读写）
- 写入操作非常频繁（不停给像素点写颜色值）
- 内部没有动态刷新机制

**结论**：LCD GRAM 按照 SRAM 类型配置 FSMC，使用 Bank 1。

📄 [原文03: LCD寻址与命令数据写入](../raw/嵌入式开发/FSMC控制器/03_LCD寻址与命令数据写入.md)

### 3.2 LCD 的命令与数据端口

LCD 模块通常有两个端口：
- **命令端口**：用于发送控制命令（如设置光标位置、写入GRAM等）
- **数据端口**用于读写像素数据

**地址计算**：
- 假设 LCD 连接 NE4（Bank1-4），基地址 = 0x6C00_0000
- 命令端口地址 = 基地址 + 偏移（通常偏移为 0x00）
- 数据端口地址 = 基地址 + 偏移（通常偏移为 0x02，因为16位数据总线）

**示例**：
```c
#define LCD_CMD   (*((volatile uint16_t *)0x6C000000))  // 命令端口
#define LCD_DATA  (*((volatile uint16_t *)0x6C000002))  // 数据端口

// 发送命令
LCD_CMD = 0x002C;  // 写入GRAM命令

// 写入像素数据
LCD_DATA = 0xF800;  // 红色
```

📄 [原文03: LCD寻址与命令数据写入](../raw/嵌入式开发/FSMC控制器/03_LCD寻址与命令数据写入.md)

### 3.3 LCD 初始化流程

典型的 LCD 初始化步骤：
1. 复位 LCD
2. 发送初始化命令序列（配置显示参数）
3. 设置显示区域（窗口）
4. 写入像素数据

**关键命令**：
- 0x002C：写入GRAM（开始写入像素数据）
- 0x002A：设置列地址
- 0x002B：设置行地址

📄 [原文03: LCD寻址与命令数据写入](../raw/嵌入式开发/FSMC控制器/03_LCD寻址与命令数据写入.md)

---

## 四、NOR Flash / PSRAM 读写时序

### 4.1 FSMC 时序控制的意义

FSMC 的核心任务是将 AHB 总线上的读写控制信号、数据、地址，转换为外部存储器可识别的通信协议时序。

**时序**：时间序列，所有信号（地址、数据、控制）按时间顺序排列，确定什么时候传地址、什么时候传数据、什么时候控制信号有效。

**本质**：FSMC 内部集成协议转换模块，自动完成时序控制，用户只需配置参数。

📄 [原文04: NOR Flash与PSRAM读写时序](../raw/嵌入式开发/FSMC控制器/04_NOR Flash与PSRAM读写时序.md)

### 4.2 时钟来源

FSMC 的时钟来源是 HCLK（AHB 高速系统总线时钟）：
- STM32F103 的 HCLK 通常为 72 MHz
- 1 个 HCLK 周期 ≈ 13.9 ns
- FSMC 的所有时序参数都以 HCLK 周期为单位

📄 [原文04: NOR Flash与PSRAM读写时序](../raw/嵌入式开发/FSMC控制器/04_NOR Flash与PSRAM读写时序.md)

### 4.3 模式 1 读时序（SRAM/PSRAM）

模式 1 是最基本的读写时序，适用于 SRAM 和 PSRAM：

**读操作时序**：
```
地址建立阶段（ADDSET）：地址有效，等待存储器准备数据
数据建立阶段（DATAST）：读使能信号有效，读取数据
```

**关键参数**：
- ADDSET：地址建立时间（HCLK 周期数）
- DATAST：数据建立时间（HCLK 周期数）

**读操作流程**：
1. CPU 发出读地址
2. FSMC 将地址放到地址总线
3. 等待 ADDSET 个 HCLK 周期（地址建立）
4. 拉低 NOE（读使能）
5. 等待 DATAST 个 HCLK 周期（数据建立）
6. 读取数据总线上的数据
7. 释放 NOE

📄 [原文04: NOR Flash与PSRAM读写时序](../raw/嵌入式开发/FSMC控制器/04_NOR Flash与PSRAM读写时序.md)

### 4.4 模式 1 写时序（SRAM/PSRAM）

**写操作时序**：
```
地址建立阶段（ADDSET）：地址有效
数据建立阶段（DATAST）：写使能信号有效，写入数据
```

**写操作流程**：
1. CPU 发出写地址和数据
2. FSMC 将地址放到地址总线，数据放到数据总线
3. 等待 ADDSET 个 HCLK 周期（地址建立）
4. 拉低 NWE（写使能）
5. 等待 DATAST 个 HCLK 周期（数据建立）
6. 释放 NWE

📄 [原文04: NOR Flash与PSRAM读写时序](../raw/嵌入式开发/FSMC控制器/04_NOR Flash与PSRAM读写时序.md)

---

## 五、IS62WV51216 SRAM 芯片详解

### 5.1 芯片概述

IS62WV51216 是一款 512K × 16 位的 SRAM 芯片：
- 容量：512K × 16 位 = 1 MB
- 数据宽度：16 位
- 工作电压：2.7V ~ 3.6V
- 访问时间：45ns / 55ns（两种速度等级）

**命名解析**：
- IS62WV：厂商型号（ISSI）
- 512K：512K 个地址（2^19 = 524,288）
- 16：16 位数据宽度

📄 [原文05: IS62WV51216 SRAM芯片详解](../raw/嵌入式开发/FSMC控制器/05_IS62WV51216 SRAM芯片详解.md)

### 5.2 引脚定义

| 引脚 | 名称 | 功能 |
|------|------|------|
| A0~A18 | 地址线 | 19 根地址线，寻址 512K 个单元 |
| IO0~IO15 | 数据线 | 16 根数据线，双向传输 |
| CS1 | 片选 | 低电平有效 |
| OE | 读使能 | 低电平有效 |
| WE | 写使能 | 低电平有效 |
| UB | 高字节使能 | 低电平有效，控制 IO8~IO15 |
| LB | 低字节使能 | 低电平有效，控制 IO0~IO7 |
| VDD | 电源 | 3.3V |
| GND | 地 | 接地 |

📄 [原文05: IS62WV51216 SRAM芯片详解](../raw/嵌入式开发/FSMC控制器/05_IS62WV51216 SRAM芯片详解.md)

### 5.3 存储容量计算

- 地址线：19 根（A0~A18）
- 可寻址单元数：2^19 = 524,288 = 512K
- 数据宽度：16 位 = 2 字节
- 总容量：512K × 2 字节 = 1 MB

📄 [原文05: IS62WV51216 SRAM芯片详解](../raw/嵌入式开发/FSMC控制器/05_IS62WV51216 SRAM芯片详解.md)

### 5.4 字节访问支持

IS62WV51216 支持字节访问：
- UB（高字节使能）：控制 IO8~IO15
- LB（低字节使能）：控制 IO0~IO7

**访问模式**：
- 16 位访问：UB=0, LB=0
- 高字节访问：UB=0, LB=1
- 低字节访问：UB=1, LB=0

📄 [原文05: IS62WV51216 SRAM芯片详解](../raw/嵌入式开发/FSMC控制器/05_IS62WV51216 SRAM芯片详解.md)

---

## 六、IS62WV51216 时序参数详解

### 6.1 关键时序参数

IS62WV51216 有两种速度等级（-55 和 -45），关键参数如下：

| 参数 | 符号 | -55 等级 | -45 等级 | 说明 |
|------|------|---------|---------|------|
| 读周期时间 | tRC | 55 ns | 45 ns | 最小读周期 |
| 地址访问时间 | tAA | 55 ns | 45 ns | 地址有效 → 数据有效 |
| OE 到数据有效 | tDOE | 25 ns | 20 ns | NOE↓ → 数据输出 |
| 写周期时间 | tWC | 55 ns | 45 ns | 最小写周期 |
| WE 脉冲宽度 | tPWE | 40 ns | 35 ns | NWE 低电平最小宽度 |
| 地址建立到写结束 | tAW | 45 ns | 40 ns | 地址有效 → NWE↑ |
| 数据建立到写结束 | tSD | 25 ns | 20 ns | 数据有效 → NWE↑ |

📄 [原文06: IS62WV51216时序参数详解](../raw/嵌入式开发/FSMC控制器/06_IS62WV51216时序参数详解.md)

### 6.2 读操作时序分析

**读操作时序图**：
```
         ┌─────────────── 一个读周期 (tRC) ───────────────┐
         │                                                │
  ADDR   ════════════════════════════════════════════════════
         │← tAA →│                                        │
  CE#    ───┐                          ┌──────────────────
            └──────────────────────────┘
  OE#    ──────┐                   ┌───────────────────────
               └───────────────────┘
               │←── tDOE ──→│
  DATA   ────────────────█████████████─────
                         ↑ 数据有效
```

**关键时序要求**：
- tAA：地址有效后，最多 55ns 数据必须有效
- tDOE：OE 有效后，最多 25ns 数据必须有效
- 数据在 OE 无效后保持 tOH 时间

📄 [原文06: IS62WV51216时序参数详解](../raw/嵌入式开发/FSMC控制器/06_IS62WV51216时序参数详解.md)

### 6.3 写操作时序分析

**写操作时序图**：
```
         ┌─────────────── 一个写周期 (tWC) ───────────────┐
         │                                                │
  ADDR   ════════════════════════════════════════════════════
         │← tSA →│                                        │
  CE#    ───┐                          ┌──────────────────
            └──────────────────────────┘
  WE#    ──────────┐           ┌───────────────────────────
                   └───────────┘
                   │← tPWE →│
  DATA   ──────────█████████████─────
                   ↑ 数据有效
```

**关键时序要求**：
- tPWE：WE 低电平最小宽度 40ns（-55等级）或 35ns（-45等级）
- tAW：地址有效到 WE 结束，最小 45ns（-55等级）或 40ns（-45等级）
- tSD：数据有效到 WE 结束，最小 25ns（-55等级）或 20ns（-45等级）

📄 [原文06: IS62WV51216时序参数详解](../raw/嵌入式开发/FSMC控制器/06_IS62WV51216时序参数详解.md)

---

## 七、FSMC 模式 1 配置详解

### 7.1 FSMC 模式 1 时序结构

FSMC 模式 1（SRAM/PSRAM）的读写时序分为两个关键阶段：
- **ADDSET**：地址建立时间
- **DATAST**：数据建立时间

**读操作时序**：
```
                  ┌── ADDSET ──┐┌────── DATAST ──────┐
  HCLK  ─┐ ┌─┐ ┌─┐ ┌─┐ ┌─┐ ┌─┐ ┌─┐ ┌─┐ ┌─┐ ┌─┐ ┌─┐
          └─┘ └─┘ └─┘ └─┘ └─┘ └─┘ └─┘ └─┘ └─┘ └─┘ └─┘
  ADDR    ════════════════════════════════════════════════
  NOE     ─────────────────────┐                   ┌─────
                               └───────────────────┘
  DATA    ─────────────────────────█████████████─────────
                                  ↑ 数据有效
```

📄 [原文07: IS62WV51216与FSMC模式1配置](../raw/嵌入式开发/FSMC控制器/07_IS62WV51216与FSMC模式1配置.md)

### 7.2 时序参数计算

**计算公式**：
- ADDSET 时间 = ADDSET × HCLK 周期
- DATAST 时间 = DATAST × HCLK 周期

**示例**（HCLK = 72 MHz，周期 ≈ 13.9 ns）：
- ADDSET = 1 → 13.9 ns
- DATAST = 2 → 27.8 ns

**配置要求**：
- ADDSET + DATAST × 2 ≥ tRC（读周期时间）
- DATAST ≥ tDOE（OE 到数据有效时间）

📄 [原文07: IS62WV51216与FSMC模式1配置](../raw/嵌入式开发/FSMC控制器/07_IS62WV51216与FSMC模式1配置.md)

### 7.3 寄存器配置

**FSMC_BCR（控制寄存器）关键位**：
- MBKEN：存储块使能
- MTYP：存储器类型（00=SRAM, 01=PSRAM, 10=NOR Flash）
- MWID：数据宽度（00=8位, 01=16位）
- WREN：写使能
- EXTMOD：扩展模式使能

**FSMC_BTR（时序寄存器）关键位**：
- ADDSET[3:0]：地址建立时间
- DATAST[7:0]：数据建立时间
- BUSTURN[3:0]：总线周转时间

📄 [原文07: IS62WV51216与FSMC模式1配置](../raw/嵌入式开发/FSMC控制器/07_IS62WV51216与FSMC模式1配置.md)

---

## 八、硬件电路设计与寄存器配置

### 8.1 IS62WV51216 与 STM32 的连线关系

STM32 通过 FSMC 的 GPIO 复用功能连接 IS62WV51216：

| 引脚 | FSMC 信号 | SRAM 引脚 | 功能 |
|------|-----------|-----------|------|
| 地址线 | A[18:0] | A0 ~ A18 | 19 根地址线 |
| 数据线 | D[15:0] | IO0 ~ IO15 | 16 根数据线 |
| 片选 | NE3 | CS1 | 片选（低有效） |
| 读使能 | NOE | OE | 读使能（低有效） |
| 写使能 | NWE | WE | 写使能（低有效） |
| 高字节使能 | NBL1 | UB | 高字节屏蔽（低有效） |
| 低字节使能 | NBL0 | LB | 低字节屏蔽（低有效） |

📄 [原文08: 硬件电路设计与寄存器配置](../raw/嵌入式开发/FSMC控制器/08_硬件电路设计与寄存器配置.md)

### 8.2 片选信号与地址空间

IS62WV51216 的 CS1 连接 NE3：
- 对应 FSMC Bank 1 的第 3 个子区（Bank1-3）
- 地址范围：0x6800_0000 ~ 0x6BFF_FFFF
- 大小：64 MB

**实际使用**：SRAM 容量 1 MB，只使用了 64 MB 地址空间的一小部分。

📄 [原文08: 硬件电路设计与寄存器配置](../raw/嵌入式开发/FSMC控制器/08_硬件电路设计与寄存器配置.md)

### 8.3 GPIO 配置

FSMC 使用的 GPIO 引脚需要配置为复用推挽输出：
- 地址线（A0~A18）：复用推挽输出
- 数据线（D0~D15）：复用推挽输出
- 控制线（NE3, NOE, NWE, NBL0, NBL1）：复用推挽输出

**配置方法**：
- 使用 CubeMX 图形化配置（推荐）
- 手动配置 GPIO 寄存器

📄 [原文08: 硬件电路设计与寄存器配置](../raw/嵌入式开发/FSMC控制器/08_硬件电路设计与寄存器配置.md)

---

## 九、FSMC 扩展外部 SRAM 寄存器方式

### 9.1 寄存器方式的优势

使用寄存器方式（不依赖标准库的 FSMC_Init 函数）配置 FSMC 的优势：
- 标准库函数封装较深，不利于理解底层原理
- 寄存器方式能看清每一位的含义，掌握 FSMC 的工作机制
- 代码更直接，便于移植和调试

📄 [原文09: FSMC扩展外部SRAM寄存器方式](../raw/嵌入式开发/FSMC控制器/09_FSMC扩展外部SRAM寄存器方式.md)

### 9.2 配置步骤

**寄存器方式配置 FSMC 的步骤**：

1. **开启时钟**：
   - 开启 FSMC 时钟
   - 开启 GPIO 时钟

2. **配置 GPIO**：
   - 配置地址线、数据线、控制线为复用推挽输出

3. **配置 FSMC_BCR**：
   - 使能存储块
   - 设置存储器类型（SRAM）
   - 设置数据宽度（16位）
   - 使能写操作

4. **配置 FSMC_BTR**：
   - 设置 ADDSET（地址建立时间）
   - 设置 DATAST（数据建立时间）

5. **使能 FSMC**：
   - 设置 FSMC_BCR 的 MBKEN 位

📄 [原文09: FSMC扩展外部SRAM寄存器方式](../raw/嵌入式开发/FSMC控制器/09_FSMC扩展外部SRAM寄存器方式.md)

### 9.3 代码示例

```c
// 1. 开启时钟
RCC->AHBENR |= RCC_AHBENR_FSMCEN;  // 开启 FSMC 时钟
RCC->APB2ENR |= RCC_APB2ENR_IOPDEN | RCC_APB2ENR_IOPEEN;  // 开启 GPIO 时钟

// 2. 配置 GPIOD (地址线 A0~A12, 数据线 D0~D7, 控制线)
// ... 省略 GPIO 配置代码 ...

// 3. 配置 FSMC_BCR (Bank1-3)
FSMC_Bank1->BTCR[4] = FSMC_BCR_MBKEN |   // 使能存储块
                       FSMC_BCR_MWID_0 |  // 16位数据宽度
                       FSMC_BCR_WREN;     // 使能写操作

// 4. 配置 FSMC_BTR
FSMC_Bank1->BTCR[5] = (1 << 0) |  // ADDSET = 1
                       (2 << 8);   // DATAST = 2

// 5. 使能 FSMC
FSMC_Bank1->BTCR[4] |= FSMC_BCR_MBKEN;
```

📄 [原文09: FSMC扩展外部SRAM寄存器方式](../raw/嵌入式开发/FSMC控制器/09_FSMC扩展外部SRAM寄存器方式.md)

---

## 十、综合复习与地址映射深入解析

### 10.1 FSMC 功能回顾

FSMC 的核心角色是"中间代理人"：
- 接收 AHB 总线上的地址、数据、控制信号
- 根据外部存储器类型转换为对应的通信协议
- 通过地址线、数据线、控制信号驱动外部存储器

**对 CPU 的效果**：CPU 访问外部存储器 = 访问片内内存，只需给地址和数据，无需关心底层通信协议。

📄 [原文10: 综合复习与地址映射深入解析](../raw/嵌入式开发/FSMC控制器/10_综合复习与地址映射深入解析.md)

### 10.2 地址映射原理

FSMC 的地址映射是**硬件级别的映射**：
- CPU 发出地址 → FSMC 解析地址 → 确定访问哪个 Bank/子区
- FSMC 自动生成片选信号、地址信号、控制信号
- 外部存储器响应 → 数据通过数据总线返回

**关键点**：地址映射是连续的，CPU 不需要知道外部存储器的物理结构。

📄 [原文10: 综合复习与地址映射深入解析](../raw/嵌入式开发/FSMC控制器/10_综合复习与地址映射深入解析.md)

### 10.3 多设备挂载

FSMC 可以同时挂载多个外部存储器：
- 每个设备连接不同的片选信号（NE1~NE4）
- 每个设备占用不同的地址空间
- CPU 通过地址自动选择访问哪个设备

**示例**：
- SRAM 连接 NE3 → 地址 0x6800_0000
- LCD 连接 NE4 → 地址 0x6C00_0000

📄 [原文10: 综合复习与地址映射深入解析](../raw/嵌入式开发/FSMC控制器/10_综合复习与地址映射深入解析.md)

---

## 十一、HAL 库调用方式

### 11.1 为什么使用 HAL 库方式

**寄存器方式的痛点**：
- FSMC 使用了大量 GPIO 引脚（地址线、数据线、控制线）
- 每个引脚都需要手动配置工作模式（复用推挽输出）
- GPIO 配置代码篇幅大、枯燥、易出错

**HAL 库方式（CubeMX 图形化配置）的优势**：
- 图形界面点选即可完成配置
- GPIO 引脚工作模式自动生成
- FSMC 参数通过下拉菜单选择
- 配置速度快、不易出错

📄 [原文11: HAL库调用方式](../raw/嵌入式开发/FSMC控制器/11_HAL库调用方式.md)

### 11.2 CubeMX 配置步骤

**FSMC 配置**：
1. 在 Connectivity 中选择 FSMC
2. 选择 Bank1（NOR Flash/PSRAM/SRAM）
3. 配置片选信号（NE1~NE4）
4. 设置存储器类型（SRAM）
5. 设置数据宽度（16位）
6. 配置时序参数（ADDSET, DATAST）

**GPIO 配置**：
- CubeMX 自动生成 FSMC 相关的 GPIO 配置
- 无需手动配置每个引脚

📄 [原文11: HAL库调用方式](../raw/嵌入式开发/FSMC控制器/11_HAL库调用方式.md)

### 11.3 HAL 库代码示例

```c
// FSMC 初始化句柄
SRAM_HandleTypeDef hsram1;

// FSMC 初始化函数
void MX_FSMC_Init(void)
{
  FSMC_NORSRAM_TimingTypeDef Timing = {0};
  
  hsram1.Instance = FSMC_NORSRAM_DEVICE;
  hsram1.Extended = FSMC_NORSRAM_EXTENDED_DEVICE;
  
  hsram1.Init.NSBank = FSMC_NORSRAM_BANK3;
  hsram1.Init.DataAddressMux = FSMC_DATA_ADDRESS_MUX_DISABLE;
  hsram1.Init.MemoryType = FSMC_MEMORY_TYPE_SRAM;
  hsram1.Init.MemoryDataWidth = FSMC_NORSRAM_MEM_BUS_WIDTH_16;
  hsram1.Init.BurstAccessMode = FSMC_BURST_ACCESS_MODE_DISABLE;
  hsram1.Init.WaitSignalPolarity = FSMC_WAIT_SIGNAL_POLARITY_LOW;
  hsram1.Init.WrapMode = FSMC_WRAP_MODE_DISABLE;
  hsram1.Init.WaitSignalActive = FSMC_WAIT_TIMING_BEFORE_WS;
  hsram1.Init.WriteOperation = FSMC_WRITE_OPERATION_ENABLE;
  hsram1.Init.WaitSignal = FSMC_WAIT_SIGNAL_DISABLE;
  hsram1.Init.ExtendedMode = FSMC_EXTENDED_MODE_DISABLE;
  hsram1.Init.AsynchronousWait = FSMC_ASYNCHRONOUS_WAIT_DISABLE;
  hsram1.Init.WriteBurst = FSMC_WRITE_BURST_DISABLE;
  
  Timing.AddressSetupTime = 1;
  Timing.AddressHoldTime = 1;
  Timing.DataSetupTime = 2;
  Timing.BusTurnAroundDuration = 0;
  Timing.CLKDivision = 16;
  Timing.DataLatency = 17;
  Timing.AccessMode = FSMC_ACCESS_MODE_A;
  
  HAL_SRAM_Init(&hsram1, &Timing, NULL);
}

// 访问外部 SRAM
#define SRAM_BASE_ADDR  ((uint32_t)0x68000000)
#define SRAM_SIZE       ((uint32_t)0x100000)  // 1MB

// 写入数据
void SRAM_Write(uint32_t addr, uint16_t data)
{
  *(__IO uint16_t*)(SRAM_BASE_ADDR + addr) = data;
}

// 读取数据
uint16_t SRAM_Read(uint32_t addr)
{
  return *(__IO uint16_t*)(SRAM_BASE_ADDR + addr);
}
```

📄 [原文11: HAL库调用方式](../raw/嵌入式开发/FSMC控制器/11_HAL库调用方式.md)

---

## 十二、关键概念速查

| 概念 | 说明 |
|------|------|
| FSMC | 灵活的静态存储器控制器，用于连接外部存储器 |
| Bank | FSMC 地址空间的分区，每个 Bank 256 MB |
| 子区 | Bank 1 的细分，每个子区 64 MB，通过 NE1~NE4 选择 |
| ADDSET | 地址建立时间，地址有效到读/写使能的时间 |
| DATAST | 数据建立时间，读/写使能有效的持续时间 |
| IS62WV51216 | 512K × 16 位 SRAM 芯片，容量 1 MB |
| 片选信号 | NE1~NE4，选择 Bank 1 的子区 |
| 模式 1 | FSMC 的基本读写时序模式，适用于 SRAM/PSRAM |
| HCLK | AHB 高速系统总线时钟，FSMC 时序的基础 |
| 寄存器方式 | 直接操作 FSMC 寄存器，不依赖标准库 |
| HAL 库方式 | 使用 CubeMX 配置，自动生成代码 |

---

## 十三、常见问题

| 问题 | 解答 |
|------|------|
| FSMC 支持哪些存储器类型？ | NOR Flash、PSRAM、SRAM、NAND Flash、PC Card |
| Bank 1 的地址范围是什么？ | 0x6000_0000 ~ 0x6FFF_FFFF（256 MB） |
| IS62WV51216 的容量是多少？ | 512K × 16 位 = 1 MB |
| 如何计算 FSMC 时序参数？ | ADDSET × HCLK周期 ≥ tAA, DATAST × HCLK周期 ≥ tDOE |
| 为什么用寄存器方式？ | 理解底层原理，便于移植和调试 |
| CubeMX 配置 FSMC 的优势？ | 自动生成 GPIO 配置，图形界面直观 |
| LCD 的 GRAM 属于什么类型？ | SRAM 类型，使用 Bank 1 |
| 如何访问外部 SRAM？ | 直接读写映射地址，如 `*(__IO uint16_t*)0x68000000` |