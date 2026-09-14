# 第六章 FSMC 控制器 — HAL 库调用方式（CubeMX 配置） 笔记

---

## 一、为什么使用 HAL 库方式

### 1.1 寄存器方式的痛点

```
寄存器方式配置 FSMC 的问题：
  → FSMC 使用了大量 GPIO 引脚（地址线、数据线、控制线）
  → 每个引脚都需要手动配置工作模式（复用推挽输出）
  → GPIO 配置代码篇幅大、枯燥、易出错
  → FSMC 寄存器配置虽然不多，但 GPIO 配置繁琐

HAL 库方式（CubeMX 图形化配置）的优势：
  → 图形界面点选即可完成配置
  → GPIO 引脚工作模式自动生成
  → FSMC 参数通过下拉菜单选择
  → 配置速度快、不易出错
```

---

## 二、CubeMX 基本配置

### 2.1 系统配置

```
与之前工程相同的配置：

① SYS
   → Debug：Serial Wire（单线调试）

② RCC
   → HSE：Crystal/Ceramic Resonator（外部高速晶振）
   → LSE：Crystal/Ceramic Resonator（外部低速晶振）

③ 时钟配置（Clock Configuration）
   → HSE → PLL × 9 = 72 MHz
   → AHB Prescaler = 1
   → APB1 Prescaler = 2（36 MHz）
   → APB2 Prescaler = 1（72 MHz）

④ USART1
   → Mode：Asynchronous（异步模式）
   → 用于串口打印输出
```

---

## 三、FSMC 图形化配置

### 3.1 找到 FSMC 配置入口

```
FSMC 的位置：
  → 左侧菜单栏 → Connectivity（连接性）
  → 不在 System Core 中
  → 因为 FSMC 本质上是连接外部设备的"通信模块"

为什么在 Connectivity 下？
  → FSMC 的本质是协议转换和外部连接
  → 类似于 I²C、SPI 等通信模块
  → 只不过它专门用于存储器扩展
```

### 3.2 选择 Bank 和子区

```
CubeMX 中 FSMC 的配置面板：

  NOR Flash / PSRAM / SRAM：
    → NOR/PSRAM/SRAM 1  ← 选择这个（序号无所谓）
    → NOR/PSRAM/SRAM 2
    → NOR/PSRAM/SRAM 3
    → NOR/PSRAM/SRAM 4

  NAND Flash：
    → NAND Flash 1
    → NAND Flash 2

  Compact Flash（PC 卡）

注意：
  → 这里的 1/2/3/4 只是序号，不代表具体的 NE 片选信号
  → 具体的片选信号在内部参数中单独配置
  → 选择哪个序号都可以，我们选择第一个
```

### 3.3 配置片选信号

```
Chip Select（片选信号）：
  → 下拉菜单中选择 NE3
  → 对应 Bank1-3，地址范围 0x6800_0000 ~ 0x6BFF_FFFF
  → 与硬件电路中 SRAM 芯片的 CS 连接的 NE3 对应
```

### 3.4 配置存储器类型

```
Memory Type（存储器类型）：
  → 下拉菜单选择 SRAM
  → 对应 BCR 寄存器的 MTYP = 00
```

### 3.5 配置地址线

```
Address（地址线）：
  → 默认为 Disable
  → 需要改为具体位数
  → 我们的 SRAM 有 19 根地址线 → 选择 19 bits
  → 最大可选 26 bits（对应 64M 地址空间）

配置后效果：
  → CubeMX 自动生成 19 个地址引脚的 GPIO 配置
  → 所有地址引脚自动配置为复用推挽输出
  → 无需手动逐个配置 GPIO
```

### 3.6 配置数据线

```
Data（数据宽度）：
  → 8 bits 或 16 bits
  → 我们的 SRAM 是 16 位 → 选择 16 bits
  → 对应 BCR 寄存器的 MWID = 01

配置后效果：
  → CubeMX 自动生成 16 个数据引脚的 GPIO 配置
  → 所有数据引脚自动配置为复用推挽输出
```

### 3.7 配置字节选择信号

```
Byte Enable（字节使能）：
  → 当数据宽度为 16 位时可选
  → 勾选后启用 NBL0（LB）和 NBL1（UB）信号
  → 支持 8 位数据访问（选择高/低字节）

配置后效果：
  → PE0 → NBL0（LB，低字节使能）
  → PE1 → NBL1（UB，高字节使能）
  → GPIO 自动配置为复用推挽输出
```

### 3.8 配置结果预览

```
CubeMX 自动生成的 GPIO 配置：

  地址线（19 根）：
    → A0 ~ A18 → 复用推挽输出
    → 分布在不同的 GPIO 端口上

  数据线（16 根）：
    → D0 ~ D15 → 复用推挽输出
    → 分布在不同的 GPIO 端口上

  控制信号：
    → NE3（PG10）→ 复用推挽输出
    → NOE        → 复用推挽输出
    → NWE        → 复用推挽输出
    → NBL0（PE0）→ 复用推挽输出
    → NBL1（PE1）→ 复用推挽输出

  → 所有 GPIO 配置全部自动生成，无需手动编写
```

---

## 四、FSMC 参数配置

### 4.1 BCR 参数（Configuration 区域）

```
在 CubeMX 的 FSMC 参数配置面板中：

① Write Enable（写使能）
   → Enable ✅
   → 对应 BCR.WREN = 1

② Extended Mode（扩展模式）
   → Disable
   → 对应 BCR.EXTMOD = 0（模式 1）
   → 选择 Disable → 读写时序共用 BTR
   → 选择 Enable → 下方出现 Mode A/B/C/D 选项
     → BTR 配置读时序
     → BWTR 配置写时序

③ 其他参数
   → Memory Type = SRAM（已配）
   → Data Width = 16 bits（已配）
   → Chip Select = NE3（已配）
```

### 4.2 BTR 参数（Timing 区域）

```
① Address Setup Time（地址建立时间）
   → 对应 BTR.ADDSET
   → 默认值：15（15 + 1 = 16 个 HCLK 周期）
   → 芯片无下限要求，可以改小
   → 保持默认 15 也可以

② Data Setup Time（数据建立时间）
   → 对应 BTR.DATASET
   → 默认值：255（255 + 1 = 256 个 HCLK 周期）
   → 芯片要求 ≥ 40 ns
   → 我们之前测试：配 2 即可工作，建议 2 ~ 71
   → 改为 71（1 μs，保守稳定）

③ Bus Turnaround Time（总线恢复时间）
   → 对应 BTR.BUSTURN
   → 默认值：15
   → 模式 1 下无要求
   → 可以改为 1（最小值）或保持默认
```

### 4.3 扩展模式配置（可选）

```
如果开启扩展模式（Extended Mode = Enable）：

  → 出现 Access Mode 选项
  → 可选 Mode A / Mode B / Mode C / Mode D
  → 出现写时序配置（BWTR）
  → Write Address Setup Time（写地址建立时间）
  → Write Data Setup Time（写数据建立时间）
  → Write Bus Turnaround Time（写总线恢复时间）

我们使用模式 1 → 不开启扩展模式 → 以上选项不出现
```

---

## 五、生成代码

### 5.1 工程设置

```
Project Manager：
  → Project Name：FSMC_SRAM_HAL
  → Toolchain/IDE：MDK-ARM
  → Generate Code（生成代码）
```

### 5.2 生成的代码结构

```
生成的代码中：

① GPIO 初始化
   → 所有 FSMC 相关的 GPIO 自动配置为复用推挽输出
   → 无需手动编写

② FSMC 初始化
   → FSMC_NORSRAM_Init()：配置 BCR 参数
   → FSMC_NORSRAM_Timing_Init()：配置 BTR 参数
   → HAL_SRAM_Init()：调用 HAL 库初始化函数

③ 文件结构
   → main.c：主函数
   → stm32f1xx_hal_msp.c：外设底层初始化（GPIO 等）
   → stm32f1xx_it.c：中断处理
```

---

## 六、Keil 工程配置

### 6.1 基本设置

```
打开生成的 Keil 工程：

① 勾选 Use MicroLIB
   → Options for Target → Target → Use MicroLIB ✅
   → 支持 printf 串口输出

② 勾选 Reset and Run
   → Options for Target → Debug → Settings →
   → Reset and Run ✅
   → 烧写后自动运行

③ 取消 Pack
   → Options for Target → Target →
   → 取消 Use Memory Layout from Target Dialog
   → 或取消相关 Pack 选项
```

---

## 七、代码实现

### 7.1 串口重定向

```c
/* 重写 fputc 函数，支持 printf 串口输出 */
#include <stdio.h>

int fputc(int ch, FILE *f)
{
    HAL_UART_Transmit(&huart1, (uint8_t *)&ch, 1, 1000);
    return ch;
}
```

### 7.2 测试代码

```c
/* 测试外部 SRAM 扩展 */

/* 方法一：使用 __attribute__ 指定变量存放地址 */
uint32_t v1 __attribute__((at(0x68000000))) = 0x12345678;
uint32_t v2 __attribute__((at(0x68000004))) = 0xABCDEFFF;

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_USART1_UART_Init();
    MX_FSMC_Init();

    /* 方法二：使用指针访问外部 SRAM 地址 */
    uint32_t v3 = *(volatile uint32_t *)0x68000008;  /* 读取 */
    *(volatile uint32_t *)0x68000008 = 0x55555555;   /* 写入 */
    v3 = *(volatile uint32_t *)0x68000008;            /* 再次读取 */

    /* 局部变量仍在片内 SRAM */
    uint32_t v4 = 0xAAAAAAAA;

    while (1)
    {
        printf("v1 = 0x%08X @ 0x%08X\r\n", v1, (uint32_t)&v1);
        printf("v2 = 0x%08X @ 0x%08X\r\n", v2, (uint32_t)&v2);
        printf("v3 = 0x%08X @ 0x%08X\r\n", v3, 0x68000008);
        printf("v4 = 0x%08X @ 0x%08X\r\n", v4, (uint32_t)&v4);
        HAL_Delay(1000);
    }
}
```

### 7.3 测试结果分析

```
预期输出：

  v1 = 0x12345678 @ 0x68000000  ← 外部 SRAM（__attribute__ 指定）
  v2 = 0xABCDEFFF @ 0x68000004  ← 外部 SRAM（__attribute__ 指定）
  v3 = 0x55555555 @ 0x68000008  ← 外部 SRAM（指针访问）
  v4 = 0xAAAAAAAA @ 0x2000xxxx  ← 片内 SRAM（局部变量，栈地址）

验证点：
  → v1、v2、v3 的地址在 0x6800_0000 起的范围内 → 外部 SRAM ✅
  → v4 的地址在 0x2000_xxxx 范围内 → 片内 SRAM ✅
  → 数据读写正确 → FSMC 扩展外部 SRAM 成功 ✅
```

---

## 八、两种方式访问外部 SRAM

### 8.1 __attribute__((at())) 方式

```c
/* 将变量强制放到指定地址 */
uint32_t v1 __attribute__((at(0x68000000))) = 0x12345678;

/* 效果：
   → 编译器将变量 v1 的存储地址固定为 0x68000000
   → 该地址在外部 SRAM 的地址空间范围内
   → 初始化时自动将 0x12345678 写入该地址
   → 后续访问 v1 就是读写外部 SRAM
*/
```

### 8.2 指针方式

```c
/* 直接用指针操作指定地址 */
#define EXT_SRAM_BASE  ((uint32_t)0x68000000)

/* 写入 */
*(volatile uint32_t *)(EXT_SRAM_BASE + 0x08) = 0x55555555;

/* 读取 */
uint32_t data = *(volatile uint32_t *)(EXT_SRAM_BASE + 0x08);

/* 效果：
   → 直接访问 0x68000008 地址
   → FSMC 将该地址映射到外部 SRAM
   → 数据通过 FSMC 地址线/数据线传输到 SRAM 芯片
   → 完成读写操作
*/
```

### 8.3 两种方式对比

| 对比项 | __attribute__ 方式 | 指针方式 |
|--------|-------------------|---------|
| 定义方式 | 变量声明时指定地址 | 直接用指针操作地址 |
| 使用方便性 | 像普通变量一样使用 | 需要通过指针解引用 |
| 地址灵活性 | 编译时固定 | 运行时可变 |
| 适用场景 | 全局变量 | 局部操作、灵活寻址 |
| volatile | 编译器自动处理 | 需要手动加 volatile |

---

## 九、HAL 库 vs 寄存器方式对比

### 9.1 配置过程对比

```
寄存器方式：
  ① 开启时钟（FSMC + GPIO）→ 手动
  ② 配置所有 GPIO 引脚（数十个）→ 手动，繁琐
  ③ 配置 BCR3 寄存器 → 手动
  ④ 配置 BTR3 寄存器 → 手动

HAL 库方式（CubeMX）：
  ① 图形界面选择 NE3 / SRAM / 19 位地址 / 16 位数据 → 点选
  ② 勾选 Byte Enable → 点选
  ③ 设置时序参数 → 输入数值
  ④ 生成代码 → 自动完成所有配置
```

### 9.2 代码量对比

| 配置项 | 寄存器方式 | HAL 库方式 |
|--------|-----------|-----------|
| 时钟开启 | 手动编写 RCC 寄存器 | 自动生成 |
| GPIO 配置 | 数十行代码（每个引脚） | 自动生成 |
| BCR 配置 | 手动编写寄存器操作 | 自动生成 |
| BTR 配置 | 手动编写寄存器操作 | 自动生成 |
| 总代码量 | 大（GPIO 部分尤其多） | 少（仅需编写业务逻辑） |

### 9.3 核心区别

```
寄存器方式：
  → 深入理解底层原理
  → 知道每一位的含义
  → 配置灵活但繁琐
  → 适合学习和理解

HAL 库方式：
  → 图形化配置，快速上手
  → 自动生成 GPIO 和外设配置
  → 不易出错
  → 适合实际项目开发

两种方式的底层效果完全相同：
  → 最终都是操作同样的寄存器
  → GPIO 配置相同（复用推挽输出）
  → FSMC 配置相同（BCR + BTR）
  → 外部 SRAM 的读写操作一致
```

---

## 十、CubeMX 配置速查

### 10.1 FSMC 配置路径

```
左侧菜单 → Connectivity → FSMC

NOR/PSRAM/SRAM 1 → 点击添加

配置面板：
  → Chip Select = NE3
  → Memory Type = SRAM
  → Address = 19 bits
  → Data Width = 16 bits
  → Byte Enable = ✅

参数面板：
  → Write Enable = Enable
  → Extended Mode = Disable
  → Address Setup Time = 15（或改小）
  → Data Setup Time = 71（或 2 ~ 71）
  → Bus Turnaround Time = 15（或 1）
```

### 10.2 关键配置对应关系

```
CubeMX 配置项          对应寄存器          对应位域
─────────────────────────────────────────────────────
Chip Select = NE3      Bank1-3            BTCR[4]/BTCR[5]
Memory Type = SRAM     BCR.MTYP           [3:2] = 00
Address = 19 bits      （确定地址线数量）    GPIO 自动配置
Data Width = 16 bits   BCR.MWID           [5:4] = 01
Byte Enable = ✅       NBL0/NBL1          PE0/PE1 自动配置
Write Enable           BCR.WREN           [12] = 1
Extended Mode = No     BCR.EXTMOD         [14] = 0
Address Setup Time     BTR.ADDSET         [3:0]
Data Setup Time        BTR.DATASET        [15:8]
Bus Turnaround Time    BTR.BUSTURN        [19:16]
```

---

## 十一、关键概念速查

| 概念 | 说明 |
|------|------|
| FSMC 所在菜单位置 | Connectivity（连接性），不在 System Core |
| Chip Select | 片选信号选择，决定地址空间范围 |
| Memory Type | 存储器类型：SRAM / PSRAM / NOR Flash / LCD |
| Address bits | 地址线位数，由外部存储器容量决定 |
| Data Width | 数据宽度：8 或 16 位 |
| Byte Enable | 字节使能（UB/LB），支持 16 位模式下的 8 位访问 |
| Write Enable | 写使能，允许写入操作 |
| Extended Mode | 扩展模式，开启后读写时序可分别配置 |
| Address Setup Time | 地址建立时间 = 值 + 1 个 HCLK 周期 |
| Data Setup Time | 数据建立时间 = 值 + 1 个 HCLK 周期 |
| Bus Turnaround Time | 总线恢复时间 |
| __attribute__((at())) | 编译器属性，将变量放到指定地址 |
| volatile | 防止编译器优化，确保每次都真正读写该地址 |
| MX_FSMC_Init() | CubeMX 生成的 FSMC 初始化函数 |
| HAL_SRAM_Init() | HAL 库的 SRAM 初始化函数 |
| 复用推挽输出 | 所有 FSMC GPIO 引脚的工作模式 |

---

## 十二、常见问题

| 问题 | 解答 |
|------|------|
| FSMC 在 CubeMX 哪里配置？ | **Connectivity → FSMC** |
| Chip Select 选哪个？ | 根据硬件连接选择，我们选 **NE3** |
| 1/2/3/4 序号代表什么？ | 只是序号，不代表具体 NE 片选，片选单独配置 |
| Address bits 配多少？ | 由外部 SRAM 容量决定，512K 单元 → **19 bits** |
| Data Width 选哪个？ | IS62WV51216 是 16 位 → **16 bits** |
| Byte Enable 要勾吗？ | **要勾**，支持 16 位模式下的 8 位数据访问 |
| Extended Mode 要开吗？ | 模式 1 → **不开**（Disable） |
| Data Setup Time 配多少？ | 建议 **2 ~ 71**，满足 40 ns 要求 |
| __attribute__ 和指针方式哪个好？ | 全局变量用 __attribute__，灵活操作用指针 |
| 两种方式底层效果一样吗？ | **完全相同**，都是操作同样的寄存器 |
| GPIO 需要手动配吗？ | **不需要**，CubeMX 自动生成所有 FSMC GPIO 配置 |
| 局部变量会放到外部 SRAM 吗？ | **不会**，局部变量在片内 SRAM 的栈空间 |