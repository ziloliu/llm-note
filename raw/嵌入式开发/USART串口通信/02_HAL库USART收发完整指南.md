# HAL 库 USART 收发完整指南

> 本文档整合了 HAL 库 USART 的轮询收发、变长数据收发、中断方式收发的完整流程。

---

## 一、CubeMX 图形化配置

### 1.1 基础配置（每个新工程必须）

| 配置项 | 操作 |
|--------|------|
| Debug | SYS → Serial Wire |
| 高速时钟 | RCC → HSE → Crystal/Ceramic Resonator |
| 低速时钟 | RCC → LSE → Crystal/Ceramic Resonator |
| 时钟树 | HSE → PLL → ×9 → 72MHz 系统时钟 |
| APB1 | /2 → 36MHz |

### 1.2 USART1 配置

| 配置项 | 路径 | 设置值 |
|--------|------|--------|
| 启用 USART1 | Connectivity → USART1 → Mode → **Asynchronous** | 开启异步模式 |
| 波特率 | Parameter Settings | **115200 Bits/s** |
| 字长 | Word Length | **8 Bits**（含校验位） |
| 校验 | Parity | **None** |
| 停止位 | Stop Bits | **1** |
| 数据方向 | Data Direction | **Receive and Transmit** |
| 硬件流控 | Hardware Flow Control | **Disable** |

### 1.3 自动配置的引脚

选择 USART1 Asynchronous 后，CubeMX 自动分配引脚：

| 引脚 | 功能 | GPIO 配置 |
|------|------|-----------|
| **PA9** | USART1_TX | 复用推挽输出（AF Push-Pull），高速 |
| **PA10** | USART1_RX | 浮空输入（No pull-up/pull-down） |

> 无需手动到引脚图中选择，CubeMX 根据模式选择自动完成引脚映射。

### 1.4 NVIC 配置

| 配置项 | 操作 |
|--------|------|
| 轮询方式 | 不勾选 NVIC 中的 USART1 中断（无需开启） |
| 中断方式 | 勾选 USART1 global interrupt → Enable |

---

## 二、CubeMX 生成的代码结构

```
Project/
├── Core/
│   ├── Src/
│   │   ├── main.c              ← 主函数
│   │   ├── usart.c             ← USART 初始化（自动生成）
│   │   ├── gpio.c              ← GPIO 初始化（自动生成）
│   │   └── stm32f1xx_it.c      ← 中断服务程序
│   └── Inc/
│       ├── main.h
│       └── usart.h
├── Drivers/
│   └── STM32F1xx_HAL_Driver/   ← HAL 库源码
└── Startup/
    └── startup_stm32f103xb.s
```

---

## 三、核心数据结构：UART_HandleTypeDef

CubeMX 自动生成的 `usart.c` 中定义了：

```c
UART_HandleTypeDef huart1;
```

### 结构体定义（HAL 库内部）

```c
typedef struct
{
    USART_TypeDef            *Instance;   // 指向 USART1 寄存器基地址
    UART_InitTypeDef         Init;        // 初始化参数（波特率、字长等）
    uint8_t                  *pTxBuffPtr; // 发送缓冲区指针
    uint16_t                 TxXferSize;  // 发送数据大小
    uint16_t                 TxXferCount; // 发送计数
    uint8_t                  *pRxBuffPtr; // 接收缓冲区指针
    uint16_t                 RxXferSize;  // 接收数据大小
    uint16_t                 RxXferCount; // 接收计数
    // ... 其他状态、回调等
} UART_HandleTypeDef;
```

> `h` 代表 Handle（句柄），是 HAL 库对 USART 外设的统一封装。所有 HAL 库函数都通过此结构体操作外设。

---

## 四、发送函数（轮询方式）

### 4.1 函数原型

```c
HAL_StatusTypeDef HAL_UART_Transmit(
    UART_HandleTypeDef *huart,   // 串口句柄指针
    const uint8_t *pData,        // 待发送数据指针（字符串/数组）
    uint16_t Size,               // 发送字节数
    uint32_t Timeout             // 超时时间（毫秒）
);
```

### 4.2 参数说明

| 参数 | 类型 | 说明 |
|------|------|------|
| huart | `UART_HandleTypeDef *` | 串口句柄地址，传入 `&huart1` |
| pData | `const uint8_t *` | 待发送数据的首地址 |
| Size | `uint16_t` | 发送的字节数（**需手动指定**） |
| Timeout | `uint32_t` | 超时毫秒数（轮询方式下有效，防止卡死） |

### 4.3 返回值

| 返回值 | 含义 |
|--------|------|
| `HAL_OK` (0x00) | 发送成功 |
| `HAL_ERROR` (0x01) | 发生错误 |
| `HAL_BUSY` (0x02) | 外设忙 |
| `HAL_TIMEOUT` (0x03) | 超时未完成 |

### 4.4 发送示例

```c
// 发送字符串（不含 \0）
uint8_t str[] = "Hello World\n";
HAL_UART_Transmit(&huart1, str, 14, 1000);

// 等价写法（使用 strlen 计算长度）
HAL_UART_Transmit(&huart1, str, strlen((char *)str), 1000);
```

---

## 五、轮询方式定长接收

### 5.1 函数原型

```c
HAL_StatusTypeDef HAL_UART_Receive(
    UART_HandleTypeDef *huart,   // 串口句柄指针
    uint8_t *pData,              // 接收缓冲区指针
    uint16_t Size,               // 期望接收的字节数（定长）
    uint32_t Timeout             // 超时时间（毫秒）
);
```

### 5.2 关键特性：定长接收

| 特性 | 说明 |
|------|------|
| Size 含义 | 指定**期望接收的字节数**（非回传实际接收数） |
| 接收行为 | 必须收到指定数量的字节才算接收成功 |
| 发送方要求 | 发送的数据量必须 **≥ Size**，否则超时等待 |
| 多余数据 | 超过 Size 的部分不会被接收，留在硬件缓冲区中 |
| 不足数据 | 未收到 Size 个字节则一直等待直到超时 |

### 5.3 定长接收示例

```c
uint8_t buffer[100];
uint16_t size = 10;

// 期望接收 10 个字节，超时 1 秒
if (HAL_UART_Receive(&huart1, buffer, size, 1000) == HAL_OK)
{
    // 接收成功，原封不动发回
    HAL_UART_Transmit(&huart1, buffer, size, 1000);
}
```

### 5.4 定长接收行为测试

| 电脑发送 | 接收 Size=10 | 结果 |
|----------|:----------:|------|
| `1234567890`（10 字节） | 收到 10 字节 | 正常回显 `1234567890` |
| `12345678`（8 字节） | 等待 1 秒后超时 | 接收失败，不回显 |
| `1234567812`（10+ 连续发） | 收到前 10 字节 | 回显 `1234567812` |
| `1234567890abcd`（14 字节） | 仅接收前 10 字节 | 回显 `1234567890`，剩余留在缓冲区 |
| 间隔 8 字节发送 | 超时后失败 | 无法正常接收 |

---

## 六、轮询方式变长接收

### 6.1 定长接收的局限性

| 问题 | 说明 |
|------|------|
| Size 固定 | `HAL_UART_Receive()` 要求预先指定接收字节数 |
| 发送方受限 | 发送的数据量必须等于 Size，否则超时或截断 |
| 不灵活 | 无法适应不同长度的字符串收发场景 |

### 6.2 变长接收函数：HAL_UARTEx_ReceiveToIdle

#### 函数原型

```c
HAL_StatusTypeDef HAL_UARTEx_ReceiveToIdle(
    UART_HandleTypeDef *huart,   // 串口句柄指针
    uint8_t *pData,              // 接收缓冲区指针
    uint16_t Size,               // 缓冲区总容量（最大可接收字节数）
    uint16_t *RxLen,             // 实际接收到的字节数（指针，用于回传）
    uint32_t Timeout             // 超时时间（毫秒）
);
```

#### 参数详解

| 参数 | 类型 | 含义 | 说明 |
|------|------|------|------|
| huart | `UART_HandleTypeDef *` | 串口句柄 | 传入 `&huart1` |
| pData | `uint8_t *` | 接收缓冲区 | 存放接收到的数据 |
| Size | `uint16_t` | 缓冲区总容量 | 最多接收多少字节（防止溢出） |
| RxLen | `uint16_t *` | 实际接收长度 | **指针**，回传真实接收到的字节数 |
| Timeout | `uint32_t` | 超时时间 | 毫秒，可用 `HAL_MAX_DELAY` 表示无限等待 |

#### Size 与 RxLen 的区别

```
Size（输入）：缓冲区能装多少 → 上限值，防止数组越界
RxLen（输出）：实际收到多少 → 真实值，回传给调用者
```

```
buffer[100]  →  Size = 100（缓冲区容量）
实际收到 8 个字节  →  *RxLen = 8（实际长度）
```

> RxLen 可以小于 Size（数据量未达上限，检测到 IDLE 即停止）。

#### 函数名含义

```
HAL_UARTEx_ReceiveToIdle
     │    │      │
     │    │      └── 接收到空闲帧（IDLE）为止
     │    └── UART 扩展功能（Ex = Extended）
     └── HAL 库前缀
```

底层原理：逐字节接收，每次收到一个字节后检查 IDLE 标志位，一旦检测到空闲帧则停止接收并返回。

### 6.3 变长接收示例

```c
#include "main.h"
#include "usart.h"
#include "gpio.h"
#include <string.h>

uint8_t buffer[100];
uint16_t size = 0;    // 注意：类型改为 uint16_t（匹配 RxLen 参数要求）

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_USART1_UART_Init();

    // 发送初始消息
    uint8_t hello[] = "Hello World\n";
    HAL_UART_Transmit(&huart1, hello, strlen((char *)hello), 1000);

    while (1)
    {
        // 变长接收：接收任意长度字符串，直到检测到空闲帧
        if (HAL_UARTEx_ReceiveToIdle(&huart1, buffer, 100, &size, HAL_MAX_DELAY) == HAL_OK)
        {
            // 接收成功，原封不动发回（长度为实际接收到的 size）
            HAL_UART_Transmit(&huart1, buffer, size, 1000);
        }
    }
}
```

### 6.4 变长接收行为测试

| 电脑发送 | 接收结果 | 回显内容 |
|----------|----------|----------|
| `1234567890`（10 字节） | size = 10 | `1234567890` |
| `12345678`（8 字节） | size = 8 | `12345678` |
| `1234567890abcd`（14 字节） | size = 14 | `1234567890abcd` |
| `Hello World\n`（12 字节） | size = 12 | `Hello World\n` |
| 中文（GBK 编码） | size = 实际字节数 | 原样回显 |

### 6.5 与定长接收函数的对比

| 对比项 | HAL_UART_Receive | HAL_UARTEx_ReceiveToIdle |
|--------|-----------------|--------------------------|
| 接收长度 | **固定**（Size 不可变） | **可变**（实际长度通过 RxLen 回传） |
| Size 含义 | 期望接收的字节数 | 缓冲区总容量（上限） |
| 结束条件 | 收满 Size 个字节 | 检测到 **IDLE 空闲帧** |
| 额外参数 | 无 | `RxLen` 指针（回传实际长度） |
| 发送方要求 | 必须发送恰好 Size 个字节 | 发送任意长度均可 |
| 适用场景 | 定长协议 | **变长数据（如字符串）** |

---

## 七、中断方式收发

### 7.1 CubeMX 配置变更（相比轮询方式）

在轮询方式的 IOC 工程基础上，仅需增加一步：

| 配置项 | 路径 | 操作 |
|--------|------|------|
| USART1 全局中断 | NVIC Settings → USART1 global interrupt | **勾选 Enable** |

其余配置（GPIO、时钟树、USART1 参数）均保持不变。

### 7.2 中断方式 vs 轮询方式的核心区别

| 对比项 | 轮询方式 | 中断方式 |
|--------|----------|----------|
| 阻塞行为 | 阻塞（CPU 空等） | **非阻塞**（CPU 可执行其他任务） |
| 超时参数 | 有 Timeout | **无 Timeout**（不需要等待） |
| 函数后缀 | 无后缀 | **_IT**（Interrupt） |
| 执行流程 | 调用函数 → 等待完成 → 返回 | 调用函数 → 立即返回 → 完成时触发回调 |
| 回调机制 | 无 | 完成后自动调用回调函数 |

### 7.3 中断方式定长接收实现

#### 使用的函数

```c
HAL_UART_Receive_IT(&huart1, buffer, 10);   // 以中断方式接收 10 字节
```

| 参数 | 说明 |
|------|------|
| &huart1 | 串口句柄地址 |
| buffer | 接收缓冲区 |
| 10 | 期望接收的字节数（定长） |
| ~~Timeout~~ | 无此参数（非阻塞，不需超时） |

#### 回调函数：HAL_UART_RxCpltCallback

```c
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART1)
    {
        is_over = 1;   // 通知主循环：接收完成
    }
}
```

#### 主循环

```c
uint8_t buffer[100];
uint16_t size = 0;
uint8_t is_over = 0;

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_USART1_UART_Init();

    HAL_UART_Receive_IT(&huart1, buffer, 10);   // 首次启动中断接收

    while (1)
    {
        if (is_over)
        {
            HAL_UART_Transmit(&huart1, buffer, 10, 1000);  // 轮询发送回显
            is_over = 0;
            HAL_UART_Receive_IT(&huart1, buffer, 10);      // 重新启动中断接收
        }
    }
}
```

#### 定长接收的局限

| 问题 | 说明 |
|------|------|
| 发送多于 10 字节 | 仅接收前 10 字节，剩余数据残留在缓冲区导致后续错位 |
| 发送少于 10 字节 | 永远收不满 10 字节，回调不触发 |
| 含回车换行 | 回车换行也占字节数，破坏定长匹配 |

### 7.4 中断方式变长接收实现

#### 使用的函数

```c
HAL_UARTEx_ReceiveToIdle_IT(&huart1, buffer, 100);
```

| 参数 | 说明 |
|------|------|
| &huart1 | 串口句柄地址 |
| buffer | 接收缓冲区 |
| 100 | 缓冲区总容量（上限，防溢出） |
| ~~RxLen~~ | 无此参数（实际长度通过回调函数传递） |
| ~~Timeout~~ | 无此参数（非阻塞） |

#### 关键变化：回调函数不同

定长接收使用 `HAL_UART_RxCpltCallback`，变长接收使用另一个回调：

```c
void HAL_UARTEx_RxEventCallback(UART_HandleTypeDef *huart, uint16_t Size)
{
    if (huart->Instance == USART1)
    {
        is_over = 1;
        size = Size;   // 回调参数 Size 即为实际接收到的字节数
    }
}
```

| 对比项 | 定长回调 | 变长回调 |
|--------|----------|----------|
| 函数名 | `HAL_UART_RxCpltCallback` | `HAL_UARTEx_RxEventCallback` |
| 额外参数 | 无 | **uint16_t Size**（实际接收长度） |
| 触发条件 | 收满指定字节数 | 检测到 **IDLE 空闲帧** |
| 所属文件 | `stm32f1xx_hal_uart.c` | `stm32f1xx_hal_uart_ex.c` |

#### 完整代码（中断变长接收）

**全局变量：**
```c
uint8_t buffer[100];
uint16_t size = 0;
uint8_t is_over = 0;
```

**回调函数（重写弱实现）：**
```c
extern uint16_t size;
extern uint8_t is_over;

void HAL_UARTEx_RxEventCallback(UART_HandleTypeDef *huart, uint16_t Size)
{
    if (huart->Instance == USART1)
    {
        is_over = 1;
        size = Size;    // 捕获实际接收长度
    }
}
```

**主函数：**
```c
int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_USART1_UART_Init();

    // 首次启动中断方式变长接收
    HAL_UARTEx_ReceiveToIdle_IT(&huart1, buffer, 100);

    while (1)
    {
        if (is_over)
        {
            // 按实际接收长度发送回显
            HAL_UART_Transmit(&huart1, buffer, size, 1000);

            is_over = 0;

            // 重新启动中断方式变长接收
            HAL_UARTEx_ReceiveToIdle_IT(&huart1, buffer, 100);
        }
    }
}
```

#### 执行流程

```
首次调用 HAL_UARTEx_ReceiveToIdle_IT() → 开启中断接收
    ↓
电脑发送数据 → 逐字节存入 buffer
    ↓
线路空闲 → 检测到 IDLE → 触发中断
    ↓
HAL_UARTEx_RxEventCallback() 被调用
    → is_over = 1
    → size = 实际接收长度
    ↓
主循环检测到 is_over == 1
    → HAL_UART_Transmit() 发送 buffer（长度 = size）
    → is_over = 0
    → HAL_UARTEx_ReceiveToIdle_IT() 重新开启接收
    ↓
回到等待状态，准备接收下一串数据
```

---

## 八、HAL 库回调函数机制

### 8.1 弱实现函数（__weak）

```c
// HAL 库源码中的默认实现（空函数）
__weak void HAL_UARTEx_RxEventCallback(UART_HandleTypeDef *huart, uint16_t Size)
{
    UNUSED(huart);
    UNUSED(Size);
}
```

- 用户在自己的代码中重新定义同名函数（不加 `__weak`）
- 编译链接时优先使用用户的强实现
- 无需修改 HAL 库源码

### 8.2 中断处理调用链

```
USART1_IRQHandler()                          ← 启动文件中断向量表定义
    ↓
HAL_UART_IRQHandler(&huart1)                 ← HAL 库统一中断处理
    ↓ 判断中断类型
HAL_UARTEx_RxEventCallback(&huart1, size)    ← 用户重写的回调函数
```

---

## 九、中断方式变长接收的注意事项

| 注意点 | 说明 |
|--------|------|
| 每次接收后需重新启动 | 回调触发后中断接收自动停止，必须再次调用 `HAL_UARTEx_ReceiveToIdle_IT()` |
| 回调函数中不要做耗时操作 | 与寄存器中断方式同理，仅设标志位，主循环处理业务逻辑 |
| size 通过回调参数传递 | 不能像轮询方式那样通过函数返回值获取，必须在回调中保存 |
| extern 声明 | 回调函数中访问全局变量需用 `extern` 声明 |
| 回调函数名不能写错 | `HAL_UARTEx_RxEventCallback`（非 `HAL_UART_RxCpltCallback`） |

---

## 十、HAL 库函数命名规律

```
HAL_  <模块名>  _<功能>

示例：
HAL_UART_Transmit()      ← 发送（transmit，非 send）
HAL_UART_Receive()       ← 接收
HAL_GPIO_TogglePin()     ← 翻转引脚
HAL_Delay()              ← 延时
```

| 查找方式 | 说明 |
|----------|------|
| 直接猜测 | `HAL_` + 模块名 + 功能英文 |
| 文件内搜索 | 打开 `stm32f1xx_hal_uart.c`，查看函数大纲 |
| 头文件查看 | `stm32f1xx_hal_uart.h` 中有所有函数声明 |

---

## 十一、轮询方式的本质

HAL 库的 `HAL_UART_Transmit` 和 `HAL_UART_Receive` 在默认模式下底层仍然是**轮询方式**：

```
Transmit 内部：
  while(等待 TXE)  →  写 DR  →  重复直到 Size 个字节发完
  → 超时保护：超过 Timeout 毫秒则返回 HAL_TIMEOUT

Receive 内部：
  while(等待 RXNE)  →  读 DR  →  重复直到 Size 个字节收满
  → 超时保护：超过 Timeout 毫秒则返回 HAL_TIMEOUT
```

> Timeout 参数是 HAL 库相对于手动轮询的改进：防止因硬件故障导致无限等待卡死。

---

## 十二、HAL 库中与 UART 相关的接收函数汇总

| 函数 | 模式 | 接收方式 | 结束条件 |
|------|------|----------|----------|
| `HAL_UART_Receive()` | 轮询 | **定长** | 收满 Size 字节 |
| `HAL_UARTEx_ReceiveToIdle()` | 轮询 | **变长** | 检测到 IDLE 空闲帧 |
| `HAL_UART_Receive_IT()` | 中断 | 定长 | 收满 Size 字节 |
| `HAL_UARTEx_ReceiveToIdle_IT()` | 中断 | 变长 | 检测到 IDLE 空闲帧 |
| `HAL_UART_Receive_DMA()` | DMA | 定长 | DMA 传输完成 |
| `HAL_UARTEx_ReceiveToIdle_DMA()` | DMA | 变长 | 检测到 IDLE 空闲帧 |

---

## 十三、HAL 库中断方式函数与回调对照表

| 接收方式 | 调用函数 | 回调函数 | 接收长度 | 结束条件 |
|----------|----------|----------|----------|----------|
| 中断定长 | `HAL_UART_Receive_IT()` | `HAL_UART_RxCpltCallback()` | 固定 | 收满 Size 字节 |
| 中断变长 | `HAL_UARTEx_ReceiveToIdle_IT()` | `HAL_UARTEx_RxEventCallback()` | **可变** | 检测到 IDLE |
| DMA 定长 | `HAL_UART_Receive_DMA()` | `HAL_UART_RxCpltCallback()` | 固定 | DMA 传输完成 |
| DMA 变长 | `HAL_UARTEx_ReceiveToIdle_DMA()` | `HAL_UARTEx_RxEventCallback()` | **可变** | 检测到 IDLE |

---

## 十四、HAL 库所有 USART 收发方式汇总

| 方式 | 发送函数 | 接收函数 | 阻塞 | 适用场景 |
|------|----------|----------|:----:|----------|
| 轮询定长 | `HAL_UART_Transmit()` | `HAL_UART_Receive()` | 是 | 简单定长收发 |
| 轮询变长 | `HAL_UART_Transmit()` | `HAL_UARTEx_ReceiveToIdle()` | 是 | 变长收发，可接受阻塞 |
| 中断定长 | `HAL_UART_Transmit_IT()` | `HAL_UART_Receive_IT()` | 否 | 定长收发，需非阻塞 |
| **中断变长** | `HAL_UART_Transmit_IT()` | **`HAL_UARTEx_ReceiveToIdle_IT()`** | **否** | **变长收发，非阻塞（推荐）** |
| DMA 定长 | `HAL_UART_Transmit_DMA()` | `HAL_UART_Receive_DMA()` | 否 | 大量数据，释放 CPU |
| DMA 变长 | `HAL_UART_Transmit_DMA()` | `HAL_UARTEx_ReceiveToIdle_DMA()` | 否 | 大量变长数据 |

---

## 十五、函数命名规律速记

```
HAL_UART_[Ex_]Receive[_IT|_DMA]

├── HAL_UART_          → HAL 库 UART 模块
├── Ex_                → 扩展功能（Extended）
├── Receive            → 接收
├── ToIdle             → 检测到空闲帧停止（变长）
├── _IT                → 中断方式（Interrupt）
└── _DMA               → DMA 方式
```

---

## 十六、寄存器方式 vs HAL 库方式对比

| 对比项 | 寄存器方式 | HAL 库方式 |
|--------|-----------|-----------|
| 初始化 | 手动配置 BRR/CR1/CR2 等寄存器 | CubeMX 图形配置 + 自动生成 |
| 发送 | while(TXE) + 写 DR | `HAL_UART_Transmit()` 一行调用 |
| 接收 | while(RXNE) + 读 DR | `HAL_UART_Receive()` 一行调用 |
| 超时保护 | 无（需自行实现） | 内置 Timeout 参数 |
| 返回状态 | 无 | HAL_OK/ERROR/BUSY/TIMEOUT |
| 接收长度 | 可变长（需自行判断结束） | **定长**（指定 Size） |
| 代码量 | 多 | **少** |
| 执行效率 | 略高 | 略低（函数调用开销） |
| 可维护性 | 依赖寄存器知识 | 函数名自解释 |

---

## 十七、CubeMX 配置速查

| 步骤 | 操作 |
|:----:|------|
| 1 | Connectivity → USART1 → Mode → Asynchronous |
| 2 | Parameter Settings：波特率 115200，8 位字长，无校验，1 停止位 |
| 3 | GPIO 自动配置：PA9 复用推挽输出，PA10 浮空输入 |
| 4 | 如需中断：NVIC → 勾选 USART1 global interrupt |
| 5 | Project Manager → 生成代码 |
| 6 | Keil 中配置 Debug → Reset and Run |

---

## 十八、HAL_MAX_DELAY 常量

```c
#define HAL_MAX_DELAY  0xFFFFFFFF   // 4294967295 毫秒 ≈ 49.7 天
```

- 表示无限等待，永远不会超时
- 适用于确定会收到数据的场景
- 等效于轮询方式的无限 while 等待，但保留了 HAL 库的状态管理机制

---

## 十九、关键注意事项

| 注意点 | 说明 |
|--------|------|
| size 类型必须匹配 | `RxLen` 参数要求 `uint16_t *`，变量声明必须为 `uint16_t` |
| 缓冲区容量要足够 | Size 参数应 ≤ buffer 实际大小，防止数组越界 |
| 函数名带 Ex | `HAL_UARTEx_ReceiveToIdle` 属于 UART 扩展功能，在 `stm32f1xx_hal_uart_ex.c` 中 |
| 底层原理仍是 IDLE | 与寄存器方式的 IDLE 检测原理一致，HAL 库封装了底层细节 |
| 中文编码 | 串口助手与系统的字符集需一致（如 GBK），否则中文显示乱码 |

---

## 二十、三种串口实现方式总结

| 方式 | 接收实现 | 变长判断 | 代码量 |
|------|----------|----------|--------|
| **寄存器 + 轮询** | while(RXNE) + 判断 IDLE | 手动实现双重循环 | 最多 |
| **寄存器 + 中断** | RXNE 中断存数据 + IDLE 中断设标志 | 中断服务程序处理 | 中等 |
| **HAL 库 + 轮询** | `HAL_UARTEx_ReceiveToIdle()` 一行调用 | 函数内部自动处理 IDLE | **最少** |
| **HAL 库 + 中断** | `HAL_UARTEx_ReceiveToIdle_IT()` | 回调函数中处理 | 最少 |