# USART 串口通信

> **来源清单**（已提炼）：
> - [x] 01_USART1中断方式接收（寄存器）
> - [x] 02_HAL库USART收发完整指南
> - [x] 03_printf重定向调试方法
>
> **更新时间**：2026-06-02

---

## 一、串口通信基础

### 1.1 轮询方式的局限性

- **CPU 空转**：while 循环等待标志位期间，CPU 无法执行任何其他任务
- **效率低下**：接收时机不可预知，CPU 长时间阻塞在等待循环中
- **不利于多任务**：无法同时处理其他外设或逻辑

📄 [原文01: USART1中断方式接收（寄存器）](../raw/嵌入式开发/USART串口通信/01_USART1中断方式接收（寄存器）.md)

### 1.2 中断方式的优势

- **CPU 利用率高**：数据到达才处理，不空等
- **主循环空闲**：可处理其他任务
- **适合实际工程**：接收时机不可预知时使用

📄 [原文01: USART1中断方式接收（寄存器）](../raw/嵌入式开发/USART串口通信/01_USART1中断方式接收（寄存器）.md)

### 1.3 轮询方式与中断方式对比

| 对比项 | 轮询方式 | 中断方式 |
|--------|----------|----------|
| CPU 利用率 | 低（空等） | **高**（数据到达才处理） |
| 接收实现 | while 循环判断 RXNE/IDLE | RXNE/IDLE 触发中断 |
| 发送实现 | while 循环判断 TXE | 仍用轮询（发送时机可控） |
| 代码复杂度 | 简单 | 稍复杂（需配 NVIC + 写中断服务程序） |
| 主循环 | 阻塞在接收等待中 | **空闲**，可处理其他任务 |
| 适用场景 | 简单调试 | 实际工程应用 |

📄 [原文01: USART1中断方式接收（寄存器）](../raw/嵌入式开发/USART串口通信/01_USART1中断方式接收（寄存器）.md)

---

## 二、CubeMX 配置（HAL 库）

### 2.1 基础配置

| 配置项 | 操作 |
|--------|------|
| Debug | SYS → Serial Wire |
| 高速时钟 | RCC → HSE → Crystal/Ceramic Resonator |
| 低速时钟 | RCC → LSE → Crystal/Ceramic Resonator |
| 时钟树 | HSE → PLL → ×9 → 72MHz 系统时钟 |
| APB1 | /2 → 36MHz |

### 2.2 USART1 配置

| 配置项 | 路径 | 设置值 |
|--------|------|--------|
| 启用 USART1 | Connectivity → USART1 → Mode → **Asynchronous** | 开启异步模式 |
| 波特率 | Parameter Settings | **115200 Bits/s** |
| 字长 | Word Length | **8 Bits**（含校验位） |
| 校验 | Parity | **None** |
| 停止位 | Stop Bits | **1** |
| 数据方向 | Data Direction | **Receive and Transmit** |
| 硬件流控 | Hardware Flow Control | **Disable** |

### 2.3 自动配置的引脚

| 引脚 | 功能 | GPIO 配置 |
|------|------|-----------|
| **PA9** | USART1_TX | 复用推挽输出（AF Push-Pull），高速 |
| **PA10** | USART1_RX | 浮空输入（No pull-up/pull-down） |

> 无需手动到引脚图中选择，CubeMX 根据模式选择自动完成引脚映射。

### 2.4 NVIC 配置

| 配置项 | 操作 |
|--------|------|
| 轮询方式 | 不勾选 NVIC 中的 USART1 中断（无需开启） |
| 中断方式 | 勾选 USART1 global interrupt → Enable |

📄 [原文02: HAL库USART收发完整指南](../raw/嵌入式开发/USART串口通信/02_HAL库USART收发完整指南.md)

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

📄 [原文02: HAL库USART收发完整指南](../raw/嵌入式开发/USART串口通信/02_HAL库USART收发完整指南.md)

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

📄 [原文02: HAL库USART收发完整指南](../raw/嵌入式开发/USART串口通信/02_HAL库USART收发完整指南.md)

---

## 五、接收函数

### 5.1 轮询方式定长接收

#### 函数原型

```c
HAL_StatusTypeDef HAL_UART_Receive(
    UART_HandleTypeDef *huart,   // 串口句柄指针
    uint8_t *pData,              // 接收缓冲区指针
    uint16_t Size,               // 期望接收的字节数（定长）
    uint32_t Timeout             // 超时时间（毫秒）
);
```

#### 关键特性：定长接收

| 特性 | 说明 |
|------|------|
| Size 含义 | 指定**期望接收的字节数**（非回传实际接收数） |
| 接收行为 | 必须收到指定数量的字节才算接收成功 |
| 发送方要求 | 发送的数据量必须 **≥ Size**，否则超时等待 |
| 多余数据 | 超过 Size 的部分不会被接收，留在硬件缓冲区中 |
| 不足数据 | 未收到 Size 个字节则一直等待直到超时 |

#### 定长接收行为测试

| 电脑发送 | 接收 Size=10 | 结果 |
|----------|:----------:|------|
| `1234567890`（10 字节） | 收到 10 字节 | 正常回显 `1234567890` |
| `12345678`（8 字节） | 等待 1 秒后超时 | 接收失败，不回显 |
| `1234567812`（10+ 连续发） | 收到前 10 字节 | 回显 `1234567812` |
| `1234567890abcd`（14 字节） | 仅接收前 10 字节 | 回显 `1234567890`，剩余留在缓冲区 |
| 间隔 8 字节发送 | 超时后失败 | 无法正常接收 |

📄 [原文02: HAL库USART收发完整指南](../raw/嵌入式开发/USART串口通信/02_HAL库USART收发完整指南.md)

### 5.2 轮询方式变长接收

#### 定长接收的局限性

| 问题 | 说明 |
|------|------|
| Size 固定 | `HAL_UART_Receive()` 要求预先指定接收字节数 |
| 发送方受限 | 发送的数据量必须等于 Size，否则超时或截断 |
| 不灵活 | 无法适应不同长度的字符串收发场景 |

#### 变长接收函数：HAL_UARTEx_ReceiveToIdle

```c
HAL_StatusTypeDef HAL_UARTEx_ReceiveToIdle(
    UART_HandleTypeDef *huart,   // 串口句柄指针
    uint8_t *pData,              // 接收缓冲区指针
    uint16_t Size,               // 缓冲区总容量（最大可接收字节数）
    uint16_t *RxLen,             // 实际接收到的字节数（指针，用于回传）
    uint32_t Timeout             // 超时时间（毫秒）
);
```

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

#### 与定长接收函数的对比

| 对比项 | HAL_UART_Receive | HAL_UARTEx_ReceiveToIdle |
|--------|-----------------|--------------------------|
| 接收长度 | **固定**（Size 不可变） | **可变**（实际长度通过 RxLen 回传） |
| Size 含义 | 期望接收的字节数 | 缓冲区总容量（上限） |
| 结束条件 | 收满 Size 个字节 | 检测到 **IDLE 空闲帧** |
| 额外参数 | 无 | `RxLen` 指针（回传实际长度） |
| 发送方要求 | 必须发送恰好 Size 个字节 | 发送任意长度均可 |
| 适用场景 | 定长协议 | **变长数据（如字符串）** |

📄 [原文02: HAL库USART收发完整指南](../raw/嵌入式开发/USART串口通信/02_HAL库USART收发完整指南.md)

### 5.3 中断方式定长接收

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

#### 定长接收的局限

| 问题 | 说明 |
|------|------|
| 发送多于 10 字节 | 仅接收前 10 字节，剩余数据残留在缓冲区导致后续错位 |
| 发送少于 10 字节 | 永远收不满 10 字节，回调不触发 |
| 含回车换行 | 回车换行也占字节数，破坏定长匹配 |

📄 [原文02: HAL库USART收发完整指南](../raw/嵌入式开发/USART串口通信/02_HAL库USART收发完整指南.md)

### 5.4 中断方式变长接收（推荐）

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

📄 [原文02: HAL库USART收发完整指南](../raw/嵌入式开发/USART串口通信/02_HAL库USART收发完整指南.md)

---

## 六、HAL 库所有 USART 收发方式汇总

| 方式 | 发送函数 | 接收函数 | 阻塞 | 适用场景 |
|------|----------|----------|:----:|----------|
| 轮询定长 | `HAL_UART_Transmit()` | `HAL_UART_Receive()` | 是 | 简单定长收发 |
| 轮询变长 | `HAL_UART_Transmit()` | `HAL_UARTEx_ReceiveToIdle()` | 是 | 变长收发，可接受阻塞 |
| 中断定长 | `HAL_UART_Transmit_IT()` | `HAL_UART_Receive_IT()` | 否 | 定长收发，需非阻塞 |
| **中断变长** | `HAL_UART_Transmit_IT()` | **`HAL_UARTEx_ReceiveToIdle_IT()`** | **否** | **变长收发，非阻塞（推荐）** |
| DMA 定长 | `HAL_UART_Transmit_DMA()` | `HAL_UART_Receive_DMA()` | 否 | 大量数据，释放 CPU |
| DMA 变长 | `HAL_UART_Transmit_DMA()` | `HAL_UARTEx_ReceiveToIdle_DMA()` | 否 | 大量变长数据 |

📄 [原文02: HAL库USART收发完整指南](../raw/嵌入式开发/USART串口通信/02_HAL库USART收发完整指南.md)

---

## 七、中断服务程序设计原则

### 7.1 初版实现（中断中直接发送）

```c
void USART1_IRQHandler(void)
{
    if (USART1->SR & USART_SR_RXNE)
    {
        // 一个字节接收完成 → 存入缓冲区
        buffer[size] = (uint8_t)USART1->DR;
        size++;
    }
    else if (USART1->SR & USART_SR_IDLE)
    {
        // 字符串接收完成
        // 1. 清除 IDLE 标志位（软件序列）
        volatile uint32_t temp;
        temp = USART1->SR;
        temp = USART1->DR;
        (void)temp;

        // 2. 直接在中断中发送（不推荐）
        USART1_SendString(buffer, size);

        // 3. 清零 size
        size = 0;
    }
}
```

### 7.2 初版的问题

| 问题 | 说明 |
|------|------|
| 中断服务程序过重 | `SendString` 内部有 while 循环轮询 TXE，长时间占用 CPU |
| 阻塞其他中断 | 发送期间无法响应其他更高优先级的中断 |
| 逻辑耦合 | 用户业务逻辑混在中断服务程序中，不便于维护 |

### 7.3 改进版：标志位通知主循环

中断服务程序**只做最轻量的工作**：接收数据 + 设置标志位。具体业务逻辑（发送回显）交给主循环处理。

```c
void USART1_IRQHandler(void)
{
    if (USART1->SR & USART_SR_RXNE)
    {
        // 一个字节接收完成 → 存入缓冲区
        buffer[size] = (uint8_t)USART1->DR;
        size++;
    }
    else if (USART1->SR & USART_SR_IDLE)
    {
        // 字符串接收完成
        // 1. 清除 IDLE 标志位
        volatile uint32_t temp;
        temp = USART1->SR;
        temp = USART1->DR;
        (void)temp;

        // 2. 仅设置标志位，通知主循环
        is_over = 1;

        // 注意：不在这里清零 size，因为主循环还要用它来发送
    }
}
```

### 7.4 改进前后对比

| 对比项 | 初版（中断中直接发送） | 改进版（标志位通知主循环） |
|--------|----------------------|--------------------------|
| 中断服务程序 | 重（含发送循环） | **轻**（仅设标志位） |
| 中断占用时间 | 长 | **短** |
| 是否阻塞其他中断 | 是 | **否** |
| 业务逻辑位置 | 中断服务程序中 | **主循环中** |
| size 清零时机 | 中断中（发送前清零会导致发送失败） | **主循环中（发送完成后清零）** |

📄 [原文01: USART1中断方式接收（寄存器）](../raw/嵌入式开发/USART串口通信/01_USART1中断方式接收（寄存器）.md)

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

📄 [原文02: HAL库USART收发完整指南](../raw/嵌入式开发/USART串口通信/02_HAL库USART收发完整指南.md)

---

## 九、中断方式变长接收的注意事项

| 注意点 | 说明 |
|--------|------|
| 每次接收后需重新启动 | 回调触发后中断接收自动停止，必须再次调用 `HAL_UARTEx_ReceiveToIdle_IT()` |
| 回调函数中不要做耗时操作 | 与寄存器中断方式同理，仅设标志位，主循环处理业务逻辑 |
| size 通过回调参数传递 | 不能像轮询方式那样通过函数返回值获取，必须在回调中保存 |
| extern 声明 | 回调函数中访问全局变量需用 `extern` 声明 |
| 回调函数名不能写错 | `HAL_UARTEx_RxEventCallback`（非 `HAL_UART_RxCpltCallback`） |

📄 [原文02: HAL库USART收发完整指南](../raw/嵌入式开发/USART串口通信/02_HAL库USART收发完整指南.md)

---

## 十、printf 重定向

### 10.1 为什么需要 printf 重定向

#### 断点调试的局限

| 问题 | 说明 |
|------|------|
| 与中断冲突 | 断点本质是软中断，会抢占系统中断优先级，破坏正常时序 |
| 影响通讯时序 | 串口收发有超时机制，断点暂停会导致数据丢失或超时 |
| 改变程序行为 | 断住期间错过中断触发窗口，导致程序行为与正常运行不一致 |

> 涉及中断、串口通讯、时序敏感的场景，断点调试不适用。

#### printf 大法的优势

| 优势 | 说明 |
|------|------|
| 不影响程序运行 | 打印输出不会暂停 CPU 执行 |
| 适合中断调试 | 可在中断服务程序中打印信息，确认是否触发及执行顺序 |
| 灵活查看变量 | 可打印任意变量值、执行路径、分支判断结果 |
| 实时观察 | 程序运行过程中持续输出信息 |

📄 [原文03: printf重定向调试方法](../raw/嵌入式开发/USART串口通信/03_printf重定向调试方法.md)

### 10.2 printf 重定向原理

#### printf 底层调用链

```
printf("Hello %d\n", 100);     ← 用户调用
    ↓ 宏定义展开
    ↓
fputc(ch, stdout);             ← 逐字符调用，将每个字符写入标准输出文件
    ↓
控制台显示                       ← PC 环境下的默认实现
```

#### 重定向思路

```
原始：fputc → 写入控制台文件 → 控制台显示
重定向：fputc → 调用串口发送 → 串口发送 → 电脑串口助手显示
```

核心：**重写 `fputc` 函数**，将"写文件"改为"串口发送字符"。

#### 重写机制

- `fputc` 在 C 标准库中已有默认实现
- 用户在自己的代码中重新定义同名函数
- 编译链接时**优先使用用户的实现**（类似 `__weak` 机制）
- 无需修改标准库源码

📄 [原文03: printf重定向调试方法](../raw/嵌入式开发/USART串口通信/03_printf重定向调试方法.md)

### 10.3 通用前置条件

#### 启用 MicroLib

| 操作 | 路径 |
|------|------|
| Keil 魔法棒 | Options for Target → Target → **勾选 Use MicroLib** |

MicroLib 是 C 标准库的精简版本，适用于嵌入式系统，包含 `stdio.h` 的基本支持。

#### 引入头文件

```c
#include <stdio.h>    // 必须引入，提供 FILE 类型定义和 printf 支持
```

#### Keil 工程配置

| 配置项 | 操作 | 说明 |
|--------|------|------|
| **Use MicroLib** | Target → 勾选 | 提供精简版 C 标准库支持（含 stdio） |
| Debug | Serial Wire | ST-Link 调试模式 |
| Reset and Run | 勾选 | 烧写后自动运行 |

📄 [原文03: printf重定向调试方法](../raw/嵌入式开发/USART串口通信/03_printf重定向调试方法.md)

### 10.4 寄存器方式实现

#### fputc 内部调用

```
printf → fputc(ch, stdout) → USART1_SendChar(ch) → 等待 TXE → 写 DR → 串口发送
```

#### 需要自写的函数

```c
void USART1_Init(void)
{
    /* 时钟使能 */
    RCC->APB2ENR |= RCC_APB2ENR_IOPAEN;
    RCC->APB2ENR |= RCC_APB2ENR_USART1EN;

    /* GPIO 配置 */
    // PA9  - TX - 复用推挽输出（1011）
    GPIOA->CRH &= ~(0xF << 4);
    GPIOA->CRH |=  (0xB << 4);
    // PA10 - RX - 浮空输入（0100）
    GPIOA->CRH &= ~(0xF << 8);
    GPIOA->CRH |=  (0x4 << 8);

    /* 串口配置 */
    USART1->BRR = 0x271;   // 115200
    USART1->CR1 |= USART_CR1_UE | USART_CR1_TE | USART_CR1_RE;
}

void USART1_SendChar(uint8_t ch)
{
    while (!(USART1->SR & USART_SR_TXE));
    USART1->DR = ch;
}
```

#### 重写 fputc 函数

```c
// ===== printf 重定向 =====
#include <stdio.h>

int fputc(int ch, FILE *f)
{
    USART1_SendChar((uint8_t)ch);
    return ch;
}
```

📄 [原文03: printf重定向调试方法](../raw/嵌入式开发/USART串口通信/03_printf重定向调试方法.md)

### 10.5 HAL 库方式实现

#### fputc 内部调用

```
printf → fputc(ch, stdout) → HAL_UART_Transmit(&huart1, &ch, 1, 1000) → HAL 库内部轮询发送 → 串口发送
```

#### 重写 fputc 函数

```c
int fputc(int ch, FILE *f)
{
    // 使用 HAL 库发送单个字符（定长 = 1）
    HAL_UART_Transmit(&huart1, (uint8_t *)&ch, 1, 1000);
    return ch;
}
```

| 参数/操作 | 说明 |
|-----------|------|
| `(uint8_t *)&ch` | 将 int 类型的 ch 取地址并强转为 `uint8_t *`，匹配函数参数类型 |
| `1` | 发送长度为 1（单个字符） |
| `1000` | 超时 1000ms |
| `return ch` | 返回发送的字符，表示成功 |

> HAL 库没有单独发送一个字符的函数，用 `HAL_UART_Transmit()` 发送长度为 1 的定长数据等效实现。

📄 [原文03: printf重定向调试方法](../raw/嵌入式开发/USART串口通信/03_printf重定向调试方法.md)

### 10.6 两种实现方式对比

| 对比项 | 寄存器方式 | HAL 库方式 |
|--------|-----------|-----------|
| fputc 内部调用 | `USART1_SendChar(ch)`（自写函数） | `HAL_UART_Transmit(&huart1, &ch, 1, 1000)` |
| 发送实现 | 等待 TXE → 写 DR | 调用库函数，一行搞定 |
| 需要自写的函数 | `USART1_Init()` + `USART1_SendChar()` | 无需自写（CubeMX 生成初始化） |
| 代码量 | 多 | 少 |
| 可移植性 | 依赖寄存器知识 | 函数名自解释 |

两种方式均需：

| 前置条件 | 说明 |
|----------|------|
| Keil 勾选 MicroLib | 提供 stdio 支持 |
| 串口已初始化 | fputc 内部依赖串口发送功能 |
| 波特率一致 | 串口助手与代码配置的波特率相同 |

📄 [原文03: printf重定向调试方法](../raw/嵌入式开发/USART串口通信/03_printf重定向调试方法.md)

### 10.7 printf 重定向原理总结

```
printf("a = %d\n", a);
    ↓
逐字符调用 fputc(ch, stdout)
    ↓ 寄存器方式               ↓ HAL 库方式
USART1_SendChar(ch)         HAL_UART_Transmit(&huart1, &ch, 1, 1000)
    ↓                          ↓
等待 TXE → 写 DR             HAL 库内部轮询发送
    ↓                          ↓
串口发送 → 电脑显示            串口发送 → 电脑显示
```

📄 [原文03: printf重定向调试方法](../raw/嵌入式开发/USART串口通信/03_printf重定向调试方法.md)

---

## 十一、printf 调试应用场景

| 场景 | 使用方式 |
|------|----------|
| 确认函数是否被调用 | 在函数入口处 `printf("Function X called\n")` |
| 确认中断是否触发 | 在中断服务程序中 `printf("IRQ triggered\n")` |
| 查看变量值 | `printf("count = %d\n", count)` |
| 确认执行分支 | 在 if/else 中分别打印不同标识 |
| 确认执行顺序 | 在多个关键位置打印带序号的信息 |
| 接收数据调试 | 在接收回调中 `printf("Received %d bytes\n", size)` |

📄 [原文03: printf重定向调试方法](../raw/嵌入式开发/USART串口通信/03_printf重定向调试方法.md)

---

## 十二、printf 支持的格式化输出

重定向后，所有 `printf` 格式化功能均可使用：

| 格式符 | 说明 | 示例 |
|--------|------|------|
| `%d` | 十进制整数 | `printf("%d", 100)` → `100` |
| `%x` | 十六进制 | `printf("%x", 255)` → `ff` |
| `%f` | 浮点数 | `printf("%f", 3.14)` → `3.140000` |
| `%s` | 字符串 | `printf("%s", "test")` → `test` |
| `%c` | 单个字符 | `printf("%c", 'A')` → `A` |
| `%%` | 百分号本身 | `printf("100%%")` → `100%` |

📄 [原文03: printf重定向调试方法](../raw/嵌入式开发/USART串口通信/03_printf重定向调试方法.md)

---

## 十三、关键注意事项

### 13.1 串口收发注意事项

| 注意点 | 说明 |
|--------|------|
| size 类型必须匹配 | `RxLen` 参数要求 `uint16_t *`，变量声明必须为 `uint16_t` |
| 缓冲区容量要足够 | Size 参数应 ≤ buffer 实际大小，防止数组越界 |
| 函数名带 Ex | `HAL_UARTEx_ReceiveToIdle` 属于 UART 扩展功能，在 `stm32f1xx_hal_uart_ex.c` 中 |
| 底层原理仍是 IDLE | 与寄存器方式的 IDLE 检测原理一致，HAL 库封装了底层细节 |
| 中文编码 | 串口助手与系统的字符集需一致（如 GBK），否则中文显示乱码 |

📄 [原文02: HAL库USART收发完整指南](../raw/嵌入式开发/USART串口通信/02_HAL库USART收发完整指南.md)

### 13.2 中断服务程序注意事项

| 注意点 | 说明 |
|--------|------|
| size 清零时机 | 必须在主循环发送完毕后再清零，不能在中断中提前清零 |
| IDLE 清除必须在中断中 | 若不清除 IDLE，会反复触发中断，程序异常 |
| 中断服务程序要轻 | 只做接收存数据 + 设标志位，不做发送等耗时操作 |
| 全局变量跨文件访问 | 通过 `extern` 在 main.c 中引用 usart.c 中定义的全局变量 |

📄 [原文01: USART1中断方式接收（寄存器）](../raw/嵌入式开发/USART串口通信/01_USART1中断方式接收（寄存器）.md)

### 13.3 printf 重定向注意事项

| 注意点 | 说明 |
|--------|------|
| MicroLib 必须启用 | 不勾选则 stdio 不可用，printf 链接失败 |
| USART1 必须先初始化 | fputc 内部调用串口发送，串口未初始化则无法输出 |
| fputc 函数名不能改 | 标准库固定调用此函数名，修改后无法链接 |
| printf 有性能开销 | 逐字符串口发送，波特率 115200 下输出大量文本会占用时间 |
| 中断中慎用大量 printf | 中断服务程序应尽量简短，大量打印可能影响实时性 |
| 波特率需与串口助手一致 | 否则显示乱码 |

📄 [原文03: printf重定向调试方法](../raw/嵌入式开发/USART串口通信/03_printf重定向调试方法.md)

---

## 十四、两种调试方法对比

| 对比项 | 断点调试 | printf 重定向 |
|--------|----------|---------------|
| 是否暂停程序 | **是**（中断执行） | **否**（不影响运行） |
| 适合场景 | 顺序执行的纯逻辑代码 | 中断、通讯、时序敏感场景 |
| 可观察内容 | 寄存器、变量、内存 | 字符串、变量值、执行路径 |
| 实时性 | 逐步观察 | 持续输出 |
| 对系统的影响 | 破坏时序 | 几乎无影响（有微小延时） |
| 灵活性 | 可修改变量/寄存器值 | 仅观察，不可修改 |
| 配置复杂度 | 无需额外配置 | 需 MicroLib + 重写 fputc |

📄 [原文03: printf重定向调试方法](../raw/嵌入式开发/USART串口通信/03_printf重定向调试方法.md)

---

## 十五、寄存器方式 vs HAL 库方式对比

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

📄 [原文02: HAL库USART收发完整指南](../raw/嵌入式开发/USART串口通信/02_HAL库USART收发完整指南.md)

---

## 十六、三种串口实现方式总结

| 方式 | 接收实现 | 变长判断 | 代码量 |
|------|----------|----------|--------|
| **寄存器 + 轮询** | while(RXNE) + 判断 IDLE | 手动实现双重循环 | 最多 |
| **寄存器 + 中断** | RXNE 中断存数据 + IDLE 中断设标志 | 中断服务程序处理 | 中等 |
| **HAL 库 + 轮询** | `HAL_UARTEx_ReceiveToIdle()` 一行调用 | 函数内部自动处理 IDLE | **最少** |
| **HAL 库 + 中断** | `HAL_UARTEx_ReceiveToIdle_IT()` | 回调函数中处理 | 最少 |

📄 [原文02: HAL库USART收发完整指南](../raw/嵌入式开发/USART串口通信/02_HAL库USART收发完整指南.md)

---

## 十七、HAL 库函数命名规律

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

📄 [原文02: HAL库USART收发完整指南](../raw/嵌入式开发/USART串口通信/02_HAL库USART收发完整指南.md)

---

## 十八、函数命名规律速记

```
HAL_UART_[Ex_]Receive[_IT|_DMA]

├── HAL_UART_          → HAL 库 UART 模块
├── Ex_                → 扩展功能（Extended）
├── Receive            → 接收
├── ToIdle             → 检测到空闲帧停止（变长）
├── _IT                → 中断方式（Interrupt）
└── _DMA               → DMA 方式
```

📄 [原文02: HAL库USART收发完整指南](../raw/嵌入式开发/USART串口通信/02_HAL库USART收发完整指南.md)

---

## 十九、CubeMX 配置速查

| 步骤 | 操作 |
|:----:|------|
| 1 | Connectivity → USART1 → Mode → Asynchronous |
| 2 | Parameter Settings：波特率 115200，8 位字长，无校验，1 停止位 |
| 3 | GPIO 自动配置：PA9 复用推挽输出，PA10 浮空输入 |
| 4 | 如需中断：NVIC → 勾选 USART1 global interrupt |
| 5 | Project Manager → 生成代码 |
| 6 | Keil 中配置 Debug → Reset and Run |

📄 [原文02: HAL库USART收发完整指南](../raw/嵌入式开发/USART串口通信/02_HAL库USART收发完整指南.md)

---

## 二十、HAL_MAX_DELAY 常量

```c
#define HAL_MAX_DELAY  0xFFFFFFFF   // 4294967295 毫秒 ≈ 49.7 天
```

- 表示无限等待，永远不会超时
- 适用于确定会收到数据的场景
- 等效于轮询方式的无限 while 等待，但保留了 HAL 库的状态管理机制

📄 [原文02: HAL库USART收发完整指南](../raw/嵌入式开发/USART串口通信/02_HAL库USART收发完整指南.md)

---

## 二十一、轮询方式的本质

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

📄 [原文02: HAL库USART收发完整指南](../raw/嵌入式开发/USART串口通信/02_HAL库USART收发完整指南.md)