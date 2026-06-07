# USART1 中断方式接收实现 

---

## 一、轮询方式的局限性

| 问题 | 说明 |
|------|------|
| CPU 空转 | while 循环等待标志位期间，CPU 无法执行任何其他任务 |
| 效率低下 | 接收时机不可预知，CPU 长时间阻塞在等待循环中 |
| 不利于多任务 | 无法同时处理其他外设或逻辑 |

**改进方向：** 接收使用中断方式，CPU 不再空等，数据到达后由中断通知 CPU 处理。

---

## 二、USART 可触发的中断事件

| 中断事件 | 状态位 | 中断使能位 | 说明 |
|----------|--------|-----------|------|
| 发送数据寄存器空 | TXE | **TXEIE** | TDR 为空可写入下一个数据 |
| 发送完成 | TC | **TCIE** | 移位寄存器全部发送完毕 |
| 接收数据就绪 | **RXNE** | **RXNEIE** | 收到一个完整字节 |
| 空闲帧检测 | **IDLE** | **IDLEIE** | 变长数据接收完毕 |
| CTS 标志 | CTS | CTSIE | 硬件流控事件 |
| 溢出错误 | ORE | — | 数据覆盖错误 |
| 噪声错误 | NE | — | 噪声检测错误 |
| 帧错误 | FE | — | 帧格式错误 |
| 校验错误 | PE | PEIE | 奇偶校验错误 |
| 断开标志 | LBD | LBDIE | LIN 断开检测 |

> 本实验重点使用 **RXNEIE**（接收一个字节中断）和 **IDLEIE**（空闲帧中断）。

---

## 三、中断方式接收设计思路

### 3.1 发送端：保持轮询方式

- 发送时机由 CPU 主动控制，CPU 本身就是要执行发送任务
- 轮询 TXE 标志位等待即可，不需要改用中断

### 3.2 接收端：改用中断方式

- 接收时机不可预知（外部设备随时可能发送数据）
- 开启 RXNE 中断：每收到一个字节触发中断，将数据存入缓冲区
- 开启 IDLE 中断：检测到空闲帧触发中断，表示一串数据接收完毕

---

## 四、初始化代码实现

### 4.1 代码（在原有基础上增加中断配置）

```c
void USART1_Init(void)
{
    /* 第1步：开启时钟 */
    RCC->APB2ENR |= RCC_APB2ENR_IOPAEN;    // GPIOA 时钟
    RCC->APB2ENR |= RCC_APB2ENR_USART1EN;  // USART1 时钟

    /* 第2步：GPIO 工作模式 */
    // PA9  - TX - 复用推挽输出（MODE=11, CNF=10 → 1011）
    GPIOA->CRH &= ~(0xF << 4);
    GPIOA->CRH |=  (0xB << 4);
    // PA10 - RX - 浮空输入（MODE=00, CNF=01 → 0100）
    GPIOA->CRH &= ~(0xF << 8);
    GPIOA->CRH |=  (0x4 << 8);

    /* 第3步：串口基本配置 */
    USART1->BRR = 0x271;   // 115200 @ 72MHz
    USART1->CR1 |= USART_CR1_UE | USART_CR1_TE | USART_CR1_RE;

    /* 第4步（新增）：开启中断使能 */
    USART1->CR1 |= USART_CR1_IDLEIE;   // 空闲帧中断使能
    USART1->CR1 |= USART_CR1_RXNEIE;   // 接收缓冲区非空中断使能

    /* 第5步（新增）：NVIC 配置 */
    NVIC_SetPriorityGrouping(NVIC_PriorityGroup_3);
    NVIC_SetPriority(USART1_IRQn, 3);
    NVIC_EnableIRQ(USART1_IRQn);
}
```

### 4.2 新增配置对照

| 步骤 | 寄存器 | 配置位 | 作用 |
|:----:|--------|--------|------|
| 4 | USART1->CR1 | IDLEIE = 1 | 开启空闲帧中断 |
| 4 | USART1->CR1 | RXNEIE = 1 | 开启接收缓冲区非空中断 |
| 5 | NVIC | PriorityGroup = 3 | 全抢占优先级模式 |
| 5 | NVIC | Priority = 3 | 设置 USART1 中断优先级 |
| 5 | NVIC | Enable | 使能 USART1 中断通道 |

---

## 五、中断服务程序实现

### 5.1 中断入口函数名

从启动文件中断向量表中查找：

```c
void USART1_IRQHandler(void);
```

### 5.2 初版实现（中断中直接发送）

```c
// 全局变量
uint8_t buffer[100];
uint8_t size = 0;

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

### 5.3 初版的问题

| 问题 | 说明 |
|------|------|
| 中断服务程序过重 | `SendString` 内部有 while 循环轮询 TXE，长时间占用 CPU |
| 阻塞其他中断 | 发送期间无法响应其他更高优先级的中断 |
| 逻辑耦合 | 用户业务逻辑混在中断服务程序中，不便于维护 |

---

## 六、改进版：标志位通知主循环

### 6.1 设计思路

中断服务程序**只做最轻量的工作**：接收数据 + 设置标志位。具体业务逻辑（发送回显）交给主循环处理。

### 6.2 全局变量

```c
// usart.c
uint8_t buffer[100];
uint8_t size = 0;
uint8_t is_over = 0;   // 接收完毕标志

// main.c 中通过 extern 引用
extern uint8_t buffer[];
extern uint8_t size;
extern uint8_t is_over;
```

### 6.3 改进后的中断服务程序

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

### 6.4 改进后的主循环

```c
#include "usart.h"

extern uint8_t buffer[];
extern uint8_t size;
extern uint8_t is_over;

int main(void)
{
    USART1_Init();

    while (1)
    {
        if (is_over)
        {
            // 发送回显
            USART1_SendString(buffer, size);

            // 清除所有状态
            is_over = 0;
            size = 0;
        }
    }
}
```

### 6.5 改进前后对比

| 对比项 | 初版（中断中直接发送） | 改进版（标志位通知主循环） |
|--------|----------------------|--------------------------|
| 中断服务程序 | 重（含发送循环） | **轻**（仅设标志位） |
| 中断占用时间 | 长 | **短** |
| 是否阻塞其他中断 | 是 | **否** |
| 业务逻辑位置 | 中断服务程序中 | **主循环中** |
| size 清零时机 | 中断中（发送前清零会导致发送失败） | **主循环中（发送完成后清零）** |

---

## 七、完整执行流程

```
┌─────────────────────────────────────────────────────┐
│  上电初始化                                          │
│  ├── GPIO 配置（PA9 复用推挽，PA10 浮空输入）          │
│  ├── USART 基本配置（BRR + UE/TE/RE）                │
│  ├── 中断使能（IDLEIE + RXNEIE）                     │
│  └── NVIC 配置（优先级 + 使能）                       │
├─────────────────────────────────────────────────────┤
│  主循环 while(1)                                     │
│  └── 检测 is_over 标志                               │
│      ├── is_over = 0 → 继续空转（CPU 可做其他事情）    │
│      └── is_over = 1 → 发送 buffer → 清零状态        │
├─────────────────────────────────────────────────────┤
│  中断：收到一个字节（RXNE）                            │
│  └── buffer[size] = DR → size++                      │
├─────────────────────────────────────────────────────┤
│  中断：检测到空闲帧（IDLE）                            │
│  ├── 清除 IDLE（读 SR + 读 DR）                      │
│  └── is_over = 1                                     │
└─────────────────────────────────────────────────────┘
```

---

## 八、关键注意事项

| 注意点 | 说明 |
|--------|------|
| size 清零时机 | 必须在主循环发送完毕后再清零，不能在中断中提前清零 |
| IDLE 清除必须在中断中 | 若不清除 IDLE，会反复触发中断，程序异常 |
| 中断服务程序要轻 | 只做接收存数据 + 设标志位，不做发送等耗时操作 |
| 全局变量跨文件访问 | 通过 `extern` 在 main.c 中引用 usart.c 中定义的全局变量 |
| 编码字符集 | 串口助手与系统字符集需一致（如 GBK），否则中文显示乱码 |

---

## 九、轮询方式与中断方式对比

| 对比项 | 轮询方式 | 中断方式 |
|--------|----------|----------|
| CPU 利用率 | 低（空等） | **高**（数据到达才处理） |
| 接收实现 | while 循环判断 RXNE/IDLE | RXNE/IDLE 触发中断 |
| 发送实现 | while 循环判断 TXE | 仍用轮询（发送时机可控） |
| 代码复杂度 | 简单 | 稍复杂（需配 NVIC + 写中断服务程序） |
| 主循环 | 阻塞在接收等待中 | **空闲**，可处理其他任务 |
| 适用场景 | 简单调试 | 实际工程应用 |