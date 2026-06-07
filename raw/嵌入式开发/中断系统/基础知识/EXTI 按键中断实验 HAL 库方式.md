---
title: "EXTI 按键中断实验 HAL 库方式"
category: "STM32/中断系统"
tags: [EXTI, 按键中断, HAL库, STM32CubeMX, 实验案例]
abstract: "EXTI 按键中断实验的 HAL 库实现方式，使用 STM32CubeMX 图形化配置和 HAL 库函数。"
source: "原创"
update_time: 2026-05-29
status: 完成
type: 实操
---

## 一句话定义

EXTI 按键中断实验的 HAL 库实现方式，通过 STM32CubeMX 图形化配置 GPIO、AFIO、EXTI 和 NVIC，使用 HAL 库函数实现按键中断控制 LED 灯。

## 核心内容

### 开发方式对比

| 对比项 | 寄存器方式 | HAL 库方式 |
|--------|-----------|-----------|
| 初始化代码 | 手动逐个配置寄存器 | STM32CubeMX 图形化配置，自动生成 |
| GPIO 配置 | 手写 CRH/ODR | CubeMX 选择引脚功能自动生成 |
| AFIO 复用选择 | 手动配置 EXTICR | 选择 GPIO_EXTI 模式自动完成 |
| EXTI 配置 | 手动配置 RTSR/IMR | 图形界面选择触发方式自动完成 |
| NVIC 配置 | 调用库函数手动设置 | 图形界面勾选使能、设置优先级 |
| 中断服务程序 | 在自建文件中手写 | 在 `stm32f1xx_it.c` 中编写 |
| 核心逻辑 | 寄存器位操作 | 调用 HAL 库函数 |

### STM32CubeMX 图形化配置

#### 基础配置

| 配置项 | 操作 |
|--------|------|
| Debug 模式 | SYS → Serial Wire（SWD） |
| 高速时钟 | RCC → HSE → Crystal/Ceramic Resonator |
| 低速时钟 | RCC → LSE → Crystal/Ceramic Resonator |
| 时钟树 | HSE → PLL → ×9 → 72MHz 系统时钟 |
| APB1 分频 | /2（36MHz，因 APB1 最高 36MHz） |

#### LED1 引脚配置（PA0）

| 配置项 | 设置值 |
|--------|--------|
| 引脚功能 | GPIO_Output |
| 默认输出电平 | High（默认熄灭） |
| 输出速度 | High |
| 输出模式 | Push Pull（推挽输出） |
| 上下拉 | No pull-up and no pull-down |
| 用户标签 | LED1 |

#### K3 按键引脚配置（PF10）

| 配置项 | 设置值 |
|--------|--------|
| 引脚功能 | **GPIO_EXTI10**（非普通 GPIO_Input） |
| GPIO mode | External Interrupt Mode with Rising edge trigger detection |
| GPIO Pull-up/Pull-down | **Pull-down**（下拉，默认低电平） |
| 用户标签 | K3 |

> 关键点：选择 `GPIO_EXTI10` 而非 `GPIO_Input`，前者自动完成 AFIO 七合一复用映射，将 PF10 连接到 EXTI10 线。

#### NVIC 配置

**使能 EXTI 中断：**
- 在 NVIC 配置页面中勾选 **EXTI line[15:10] interrupts** → **Enable**

**优先级配置：**
- EXTI15_10：抢占优先级设为 **2**
- SysTick：抢占优先级保持 **15**（最低）

> 重要：HAL 库的 `HAL_Delay()` 底层依赖 SysTick 中断计时。若 EXTI15_10 优先级高于或等于 SysTick，在中断服务程序中调用 `HAL_Delay()` 会导致 SysTick 中断无法打断当前中断，延时函数卡死。因此必须确保 **SysTick 优先级高于（数值小于）EXTI15_10**。

| 中断源 | 抢占优先级 | 说明 |
|--------|-----------|------|
| SysTick | 15（或任意低于 EXTI 的值） | 必须能被 EXTI 中断打断，HAL_Delay 才能正常工作 |
| EXTI15_10 | 2 | 按键中断处理 |

### 代码生成后的工程结构

```
Project/
├── Core/
│   ├── Inc/
│   │   ├── main.h
│   │   ├── stm32f1xx_it.h
│   │   └── stm32f1xx_hal_conf.h
│   └── Src/
│       ├── main.c              ← 主函数
│       ├── gpio.c              ← GPIO 初始化（CubeMX 自动生成）
│       └── stm32f1xx_it.c      ← 中断服务程序（需手动补充逻辑）
├── Drivers/
│   ├── STM32F1xx_HAL_Driver/   ← HAL 库源码
│   └── CMSIS/                  ← ARM 内核支持
└── Startup/
    └── startup_stm32f103xb.s   ← 启动文件（含中断向量表）
```

### CubeMX 自动生成的关键初始化

| 函数 | 位置 | 功能 |
|------|------|------|
| `MX_GPIO_Init()` | gpio.c | PA0 推挽输出 + PF10 外部中断下拉输入 |
| `MX_NVIC_Init()` | main.c | 使能 EXTI15_10 中断 + 设置优先级 |
| `HAL_Init()` | main.c | HAL 库初始化（含 SysTick 配置） |
| `SystemClock_Config()` | main.c | 时钟树配置 |

### 中断服务程序实现（stm32f1xx_it.c）

#### 自动生成的中断入口

CubeMX 自动生成以下中断服务函数框架：

```c
void EXTI15_10_IRQHandler(void)
{
    HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_10);  // 调用 HAL 库的 EXTI 处理函数
}
```

`HAL_GPIO_EXTI_IRQHandler()` 内部完成：
1. 清除中断挂起标志位（PR 寄存器写 1 清零）
2. 调用回调函数 `HAL_GPIO_EXTI_Callback()`

#### 回调函数机制

HAL 库中 `HAL_GPIO_EXTI_Callback()` 被声明为 `__weak` 弱实现函数：

```c
__weak void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    // 默认为空实现，用户可重写
}
```

**`__weak` 关键字说明：**

| 特性 | 说明 |
|------|------|
| 来源 | ARM 编译器扩展关键字（借鉴 C++ 语法），非 C 标准关键字 |
| 含义 | 弱实现函数，允许用户在其他文件中重新定义同名函数覆盖它 |
| 匹配机制 | 编译器链接时优先选择用户定义的强实现（不带 `__weak` 的版本） |
| 用途 | HAL 库预留的回调接口，用户重写即可插入自定义逻辑 |

#### 两种实现方式

**方式一：直接在中断服务函数中编写逻辑**

```c
void EXTI15_10_IRQHandler(void)
{
    HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_10);  // 自动清零 PR
    // 直接在此处编写防抖、翻转等逻辑
}
```

**方式二（推荐）：重写回调函数**

```c
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    // 1. 判断具体是哪个引脚触发的中断
    if (GPIO_Pin == K3_Pin)          // 即 GPIO_PIN_10
    {
        // 2. 软件防抖延时
        HAL_Delay(10);

        // 3. 再次确认 PF10 仍为高电平
        if (HAL_GPIO_ReadPin(K3_GPIO_Port, K3_Pin) == GPIO_PIN_SET)
        {
            // 4. 翻转 LED1 状态
            HAL_GPIO_TogglePin(LED1_GPIO_Port, LED1_Pin);
        }
    }
}
```

#### 方式二的优势

| 优势 | 说明 |
|------|------|
| 引脚参数化 | 回调函数接收 `GPIO_Pin` 参数，可判断具体触发引脚 |
| 多中断复用 | EXTI15_10 共享同一入口，不同引脚可在回调中分别处理 |
| 代码解耦 | 中断入口（HAL 已处理）与业务逻辑（用户回调）分离 |
| 可移植性 | 回调函数可在任意文件中重写，不依赖特定文件结构 |

### 主函数（main.c）

```c
int main(void)
{
    HAL_Init();                    // HAL 库初始化
    SystemClock_Config();          // 时钟配置（72MHz）
    MX_GPIO_Init();                // GPIO 初始化（LED1 + K3）
    MX_NVIC_Init();                // NVIC 配置（使能 + 优先级）

    while (1)
    {
        // 无需任何操作，按键中断在回调函数中处理
    }
}
```

### HAL 库关键函数速查

| 函数 | 功能 | 所属文件 |
|------|------|----------|
| `HAL_GPIO_ReadPin(GPIOx, GPIO_Pin)` | 读取引脚电平，返回 `GPIO_PIN_SET` 或 `GPIO_PIN_RESET` | stm32f1xx_hal_gpio.c |
| `HAL_GPIO_WritePin(GPIOx, GPIO_Pin, PinState)` | 设置引脚输出电平 | stm32f1xx_hal_gpio.c |
| `HAL_GPIO_TogglePin(GPIOx, GPIO_Pin)` | 翻转引脚输出电平 | stm32f1xx_hal_gpio.c |
| `HAL_GPIO_EXTI_IRQHandler(GPIO_Pin)` | EXTI 中断处理（清零 PR + 调用回调） | stm32f1xx_hal_gpio.c |
| `HAL_GPIO_EXTI_Callback(GPIO_Pin)` | 用户重写的中断回调函数（`__weak`） | stm32f1xx_hal_gpio.c |
| `HAL_Delay(ms)` | 毫秒延时（依赖 SysTick 中断） | stm32f1xx_hal.c |

### 两种实现方式完整对比

| 对比项 | 寄存器方式 | HAL 库方式 |
|--------|-----------|-----------|
| 工程搭建 | 手动创建文件和目录 | CubeMX 自动生成 |
| 时钟使钟 | `RCC->APB2ENR \|= ...` | `MX_GPIO_Init()` 自动完成 |
| GPIO 模式 | 手动配置 CRH/CNF/MODE/ODR | CubeMX 下拉选择 |
| AFIO 映射 | `AFIO->EXTICR[2] \|= 0x0005` | 选择 GPIO_EXTI 自动完成 |
| EXTI 触发 | `EXTI->RTSR \|= ...` | CubeMX 选择边沿类型 |
| EXTI 屏蔽 | `EXTI->IMR \|= ...` | 自动生成 |
| NVIC 配置 | `NVIC_SetPriorityGrouping()` + `NVIC_EnableIRQ()` | CubeMX 图形配置 |
| PR 清零 | `EXTI->PR = EXTI_PR_PR10` | `HAL_GPIO_EXTI_IRQHandler()` 自动完成 |
| 读引脚 | `GPIOF->IDR & GPIO_IDR_IDR10` | `HAL_GPIO_ReadPin()` |
| 翻转 LED | `GPIOA->ODR ^= GPIO_ODR_ODR0` | `HAL_GPIO_TogglePin()` |
| 代码量 | 较多（底层细节多） | 较少（库函数封装） |
| 可读性 | 需了解寄存器含义 | 函数名自解释 |
| 执行效率 | 略高（无函数调用开销） | 略低（多层函数调用） |

## 注意事项 & 踩坑

- **SysTick 与 EXTI 优先级冲突**: HAL 库的 `HAL_Delay()` 依赖 SysTick 中断，若 EXTI 优先级高于或等于 SysTick，在中断服务程序中调用 `HAL_Delay()` 会导致程序卡死
- **CubeMX 引脚功能选择**: 必须选择 `GPIO_EXTI10` 而非 `GPIO_Input`，前者自动完成 AFIO 映射
- **回调函数机制**: HAL 库使用 `__weak` 关键字定义弱实现函数，用户重写即可插入自定义逻辑
- **中断服务程序**: CubeMX 自动生成中断入口，用户只需在回调函数中编写业务逻辑
- **工程配置**: Keil 中需勾选 "Reset and Run"，取消勾选 "Load Application at Startup"

## 相关笔记

- [[EXTI 按键中断实验]]
- [[外部中断控制器 EXTI]]
- [[STM32 中断体系架构]]
- [[NVIC 嵌套向量中断控制器]]

## 参考来源

- STM32F103 参考手册 RM0008
- STM32CubeMX 用户手册
- HAL 库用户手册
- 原始笔记：EXTI 按键中断实验 HAL 库方式.md