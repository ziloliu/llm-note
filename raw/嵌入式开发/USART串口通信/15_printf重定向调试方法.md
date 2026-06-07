# printf 重定向调试方法

> 本文档整合了寄存器方式和 HAL 库方式两种 printf 重定向实现方法。

---

## 一、为什么需要 printf 重定向

### 1.1 断点调试的局限

| 问题 | 说明 |
|------|------|
| 与中断冲突 | 断点本质是软中断，会抢占系统中断优先级，破坏正常时序 |
| 影响通讯时序 | 串口收发有超时机制，断点暂停会导致数据丢失或超时 |
| 改变程序行为 | 断住期间错过中断触发窗口，导致程序行为与正常运行不一致 |

> 涉及中断、串口通讯、时序敏感的场景，断点调试不适用。

### 1.2 printf 大法的优势

| 优势 | 说明 |
|------|------|
| 不影响程序运行 | 打印输出不会暂停 CPU 执行 |
| 适合中断调试 | 可在中断服务程序中打印信息，确认是否触发及执行顺序 |
| 灵活查看变量 | 可打印任意变量值、执行路径、分支判断结果 |
| 实时观察 | 程序运行过程中持续输出信息 |

---

## 二、printf 重定向原理

### 2.1 问题

- STM32 没有控制台（Console），`printf` 默认输出目标不存在
- 需要将 `printf` 的输出重定向到串口，通过串口助手在电脑端查看

### 2.2 printf 底层调用链

```
printf("Hello %d\n", 100);     ← 用户调用
    ↓ 宏定义展开
    ↓
fputc(ch, stdout);             ← 逐字符调用，将每个字符写入标准输出文件
    ↓
控制台显示                       ← PC 环境下的默认实现
```

### 2.3 重定向思路

```
原始：fputc → 写入控制台文件 → 控制台显示
重定向：fputc → 调用串口发送 → 串口发送 → 电脑串口助手显示
```

核心：**重写 `fputc` 函数**，将"写文件"改为"串口发送字符"。

### 2.4 重写机制

- `fputc` 在 C 标准库中已有默认实现
- 用户在自己的代码中重新定义同名函数
- 编译链接时**优先使用用户的实现**（类似 `__weak` 机制）
- 无需修改标准库源码

---

## 三、通用前置条件

### 3.1 启用 MicroLib

| 操作 | 路径 |
|------|------|
| Keil 魔法棒 | Options for Target → Target → **勾选 Use MicroLib** |

MicroLib 是 C 标准库的精简版本，适用于嵌入式系统，包含 `stdio.h` 的基本支持。

### 3.2 引入头文件

```c
#include <stdio.h>    // 必须引入，提供 FILE 类型定义和 printf 支持
```

### 3.3 Keil 工程配置

| 配置项 | 操作 | 说明 |
|--------|------|------|
| **Use MicroLib** | Target → 勾选 | 提供精简版 C 标准库支持（含 stdio） |
| Debug | Serial Wire | ST-Link 调试模式 |
| Reset and Run | 勾选 | 烧写后自动运行 |

---

## 四、寄存器方式实现

### 4.1 fputc 内部调用

```
printf → fputc(ch, stdout) → USART1_SendChar(ch) → 等待 TXE → 写 DR → 串口发送
```

### 4.2 需要自写的函数

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

### 4.3 重写 fputc 函数

```c
// ===== printf 重定向 =====
#include <stdio.h>

int fputc(int ch, FILE *f)
{
    USART1_SendChar((uint8_t)ch);
    return ch;
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| ch | `int` | 待发送的字符（ASCII 码值） |
| f | `FILE *` | 文件指针（串口场景下不使用，忽略即可） |
| 返回值 | `int` | 成功时返回 ch 本身，失败返回 EOF |

### 4.4 完整代码示例

**usart.c：**
```c
#include "usart.h"

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

// ===== printf 重定向 =====
#include <stdio.h>

int fputc(int ch, FILE *f)
{
    USART1_SendChar((uint8_t)ch);
    return ch;
}
```

**main.c：**
```c
#include "stm32f10x.h"
#include "usart.h"
#include <stdio.h>

int main(void)
{
    USART1_Init();

    // 打印固定字符串
    printf("Hello World\n");

    // 打印变量值
    int a = 100;
    printf("a = %d\n", a);

    while (1)
    {
        // 可在任意位置使用 printf 调试
    }
}
```

---

## 五、HAL 库方式实现

### 5.1 fputc 内部调用

```
printf → fputc(ch, stdout) → HAL_UART_Transmit(&huart1, &ch, 1, 1000) → HAL 库内部轮询发送 → 串口发送
```

### 5.2 CubeMX 配置

与之前串口配置完全一致，无需额外操作：

| 配置项 | 操作 |
|--------|------|
| Debug | Serial Wire |
| RCC | HSE + LSE |
| 时钟树 | HSE → PLL ×9 → 72MHz，APB1 /2 |
| USART1 | Asynchronous 模式，115200，8位，无校验，1停止位 |
| NVIC | **不开启**中断（轮询发送即可） |

> 仅用于 printf 输出，只需发送功能，轮询方式即可，无需中断。

### 5.3 重写 fputc 函数

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

### 5.4 完整代码

**usart.c（CubeMX 自动生成）：**
```c
UART_HandleTypeDef huart1;

void MX_USART1_UART_Init(void)
{
    huart1.Instance = USART1;
    huart1.Init.BaudRate = 115200;
    huart1.Init.WordLength = UART_WORDLENGTH_8B;
    huart1.Init.StopBits = UART_STOPBITS_1;
    huart1.Init.Parity = UART_PARITY_NONE;
    huart1.Init.Mode = UART_MODE_TX_RX;
    huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart1.Init.OverSampling = UART_OVERSAMPLING_16;
    HAL_UART_Init(&huart1);
}
```

**usart.c 用户代码区（重写 fputc）：**
```c
/* USER CODE BEGIN 0 */
#include <stdio.h>

int fputc(int ch, FILE *f)
{
    HAL_UART_Transmit(&huart1, (uint8_t *)&ch, 1, 1000);
    return ch;
}
/* USER CODE END 0 */
```

**main.c：**
```c
#include "main.h"
#include "usart.h"
#include "gpio.h"
#include <stdio.h>

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_USART1_UART_Init();

    printf("Hello World\n");

    int a = 100;
    printf("a = %d\n", a);

    while (1)
    {
    }
}
```

---

## 六、两种实现方式对比

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

---

## 七、printf 重定向原理总结

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

---

## 八、printf 支持的格式化输出

重定向后，所有 `printf` 格式化功能均可使用：

| 格式符 | 说明 | 示例 |
|--------|------|------|
| `%d` | 十进制整数 | `printf("%d", 100)` → `100` |
| `%x` | 十六进制 | `printf("%x", 255)` → `ff` |
| `%f` | 浮点数 | `printf("%f", 3.14)` → `3.140000` |
| `%s` | 字符串 | `printf("%s", "test")` → `test` |
| `%c` | 单个字符 | `printf("%c", 'A')` → `A` |
| `%%` | 百分号本身 | `printf("100%%")` → `100%` |

---

## 九、printf 调试应用场景

| 场景 | 使用方式 |
|------|----------|
| 确认函数是否被调用 | 在函数入口处 `printf("Function X called\n")` |
| 确认中断是否触发 | 在中断服务程序中 `printf("IRQ triggered\n")` |
| 查看变量值 | `printf("count = %d\n", count)` |
| 确认执行分支 | 在 if/else 中分别打印不同标识 |
| 确认执行顺序 | 在多个关键位置打印带序号的信息 |
| 接收数据调试 | 在接收回调中 `printf("Received %d bytes\n", size)` |

---

## 十、注意事项

| 注意点 | 说明 |
|--------|------|
| MicroLib 必须启用 | 不勾选则 stdio 不可用，printf 链接失败 |
| USART1 必须先初始化 | fputc 内部调用串口发送，串口未初始化则无法输出 |
| fputc 函数名不能改 | 标准库固定调用此函数名，修改后无法链接 |
| printf 有性能开销 | 逐字符串口发送，波特率 115200 下输出大量文本会占用时间 |
| 中断中慎用大量 printf | 中断服务程序应尽量简短，大量打印可能影响实时性 |
| 波特率需与串口助手一致 | 否则显示乱码 |

---

## 十一、两种调试方法对比

| 对比项 | 断点调试 | printf 重定向 |
|--------|----------|---------------|
| 是否暂停程序 | **是**（中断执行） | **否**（不影响运行） |
| 适合场景 | 顺序执行的纯逻辑代码 | 中断、通讯、时序敏感场景 |
| 可观察内容 | 寄存器、变量、内存 | 字符串、变量值、执行路径 |
| 实时性 | 逐步观察 | 持续输出 |
| 对系统的影响 | 破坏时序 | 几乎无影响（有微小延时） |
| 灵活性 | 可修改变量/寄存器值 | 仅观察，不可修改 |
| 配置复杂度 | 无需额外配置 | 需 MicroLib + 重写 fputc |