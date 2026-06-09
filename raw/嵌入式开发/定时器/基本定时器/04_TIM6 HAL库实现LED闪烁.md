# 基本定时器 TIM6 — HAL 库实现 LED 闪烁 笔记

---

## 一、CubeMX 配置

### 1.1 基础配置

| 配置项 | 路径 | 设置 |
|--------|------|------|
| Debug | SYS | Serial Wire |
| Time Base | SYS | SysTick（默认） |
| RCC | HSE + LSE | 外部高速/低速晶振 |
| 时钟树 | HSE → PLL ×9 | 72MHz，APB1 /2 → 36MHz |

### 1.2 TIM6 配置

| 配置项 | Parameter Settings | 值 |
|--------|-------------------|:--:|
| **Activate** | Timers → TIM6 → 勾选 Activate | ✅ |
| **Prescaler** (PSC) | 7199 | 7200 分频 → 10kHz |
| **Counter Mode** | Up | 向上计数（基本定时器只能向上） |
| **Counter Period** (ARR) | 9999 | 10000 次计数 → 1s |
| Auto-reload preload | Disable（默认） | ARR 写入后立即生效 |
| Trigger Event Selection | Reset（默认） | 不连接其他外设 |

### 1.3 NVIC 配置

| 配置项 | 路径 | 设置 |
|--------|------|------|
| TIM6 全局中断 | NVIC → TIM6 global interrupt | **勾选 Enable** |
| 抢占优先级 | 默认 | **0**（最高优先级） |

### 1.4 GPIO 配置（LED2）

| 引脚 | 配置 | 标签 |
|------|------|------|
| PA1 | GPIO_Output, High, Push-Pull, High Speed | **LED2** |

---

## 二、CubeMX 生成的初始化代码

### 2.1 TIM6 句柄

```c
TIM_HandleTypeDef htim6;    // 类似于 huart1, hi2c2
```

### 2.2 MX_TIM6_Init() 生成内容

```c
// CubeMX 自动生成的初始化函数（tim.c 中）
void MX_TIM6_Init(void)
{
    htim6.Instance = TIM6;
    htim6.Init.Prescaler = 7199;
    htim6.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim6.Init.Period = 9999;
    htim6.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
    HAL_TIM_Base_Init(&htim6);
}
```

> 包含在 `HAL_Init()` → `SystemClock_Config()` → `MX_GPIO_Init()` → **`MX_TIM6_Init()`** 的调用链中。

---

## 三、关键问题：CEN 未开启

### 3.1 问题现象

CubeMX 生成的代码**不会自动开启定时器**（CEN = 0），需要手动调用启动函数。

### 3.2 解决方案

```c
// 在 main() 中手动启动定时器（带中断）
HAL_TIM_Base_Start_IT(&htim6);
```

### 3.3 HAL_TIM_Base 相关函数

| 函数 | 功能 | 中断 | DMA |
|------|------|:----:|:---:|
| `HAL_TIM_Base_Start()` | 启动定时器（无中断） | ❌ | ❌ |
| **`HAL_TIM_Base_Start_IT()`** | 启动定时器（**带中断**） | ✅ | ❌ |
| `HAL_TIM_Base_Start_DMA()` | 启动定时器（带 DMA） | — | ✅ |

> 本实验使用中断方式，选择 `HAL_TIM_Base_Start_IT()`。

### 3.4 函数内部做了什么

```c
HAL_TIM_Base_Start_IT(&htim6) 内部：
  ├── __HAL_TIM_ENABLE_IT(&htim6, TIM_IT_UPDATE)  // 使能更新中断 (UIE=1)
  └── __HAL_TIM_ENABLE(&htim6)                     // 使能定时器 (CEN=1)
```

---

## 四、中断回调机制

### 4.1 HAL 库中断处理流程

```
TIM6_IRQHandler()                     // stm32f1xx_it.c（中断入口）
    │
    └── HAL_TIM_IRQHandler(&htim6)    // HAL 库（通用中断处理）
        │
        ├── 清除中断标志位（自动处理 UIF）
        ├── 判断中断类型（更新/捕获/比较等）
        └── 调用对应回调函数
            │
            └── HAL_TIM_PeriodElapsedCallback(&htim6)  // 用户重写
```

### 4.2 回调函数说明

| 回调函数 | 触发条件 | 本实验 |
|----------|----------|:------:|
| `HAL_TIM_PeriodElapsedCallback()` | **计数周期结束**（更新事件） | ✅ 使用 |
| `HAL_TIM_OC_DelayElapsedCallback()` | 输出比较延迟 | — |
| `HAL_TIM_IC_CaptureCallback()` | 输入捕获 | — |
| `HAL_TIM_PWM_PulseFinishedCallback()` | PWM 脉冲完成 | — |

### 4.3 回调函数特点

```
HAL_TIM_PeriodElapsedCallback：
  → __weak 弱实现函数，用户可重写
  → 参数 htim：定时器句柄指针（可判断是哪个定时器触发）
  → 内部已自动清除 UIF 标志位
  → 用户只需写业务逻辑
```

---

## 五、代码实现

### 5.1 main.c

```c
#include "main.h"
#include "tim.h"
#include "gpio.h"

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_TIM6_Init();

    /* 启动定时器（带中断） */
    HAL_TIM_Base_Start_IT(&htim6);

    while (1)
    {
        // 空循环
    }
}
```

### 5.2 stm32f1xx_it.c — 中断入口

```c
// CubeMX 自动生成，无需修改
void TIM6_IRQHandler(void)
{
    HAL_TIM_IRQHandler(&htim6);    // 调用 HAL 库通用中断处理
}
```

### 5.3 用户回调函数（在 stm32f1xx_it.c 底部或 main.c 中）

```c
/* 重写周期回调函数 */
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
    if (htim->Instance == TIM6)        // 判断是否为 TIM6
    {
        HAL_GPIO_TogglePin(GPIOA, LED2_Pin);   // 翻转 LED2
    }
}
```

### 5.4 为什么需要判断 htim->Instance

```
HAL_TIM_PeriodElapsedCallback 是所有定时器共享的回调函数
  → TIM2、TIM3、TIM4... 都可能触发此回调
  → 必须通过 htim->Instance 判断是哪个定时器

判断方式：
  if (htim->Instance == TIM6)   → TIM6 的中断
  if (htim->Instance == TIM2)   → TIM2 的中断
  if (htim->Instance == TIM3)   → TIM3 的中断
```

---

## 六、htim->Instance 详解

```c
// TIM_HandleTypeDef 结构体
typedef struct
{
    TIM_TypeDef              *Instance;   // 指向定时器寄存器基地址
    TIM_Base_InitTypeDef     Init;
    // ...
} TIM_HandleTypeDef;

// TIM_TypeDef 结构体（定时器寄存器映射）
typedef struct
{
    __IO uint32_t CR1;
    __IO uint32_t CR2;
    __IO uint32_t SMCR;
    __IO uint32_t DIER;
    __IO uint32_t SR;
    __IO uint32_t EGR;
    // ...
} TIM_TypeDef;

// TIM6 定义
#define TIM6  ((TIM_TypeDef *)TIM6_BASE)

// 使用
htim6.Instance = TIM6;    // 指向 TIM6 的寄存器地址空间

// 判断方式
if (htim->Instance == TIM6)   // 比较指针地址
```

---

## 七、完整执行流程

```
系统上电
    │
    ├── HAL_Init()              → 复位外设、初始化 SysTick
    ├── SystemClock_Config()    → 配置系统时钟 72MHz
    ├── MX_GPIO_Init()          → PA1 推挽输出（LED2）
    ├── MX_TIM6_Init()          → TIM6 初始化
    │   ├── PSC = 7199          → 7200 分频
    │   ├── ARR = 9999          → 10000 次计数
    │   └── HAL_TIM_Base_Init() → 配置定时器
    │
    ├── HAL_TIM_Base_Start_IT(&htim6)   → 启动定时器 + 使能中断
    │
    ├── main while(1)           → 空循环
    │
    └── 每 1s 触发中断链：
        TIM6_IRQHandler()
            → HAL_TIM_IRQHandler()
                → HAL_TIM_PeriodElapsedCallback()
                    → HAL_GPIO_TogglePin(LED2)
```

---

## 八、HAL 库 vs 寄存器方式对比

| 对比项 | 寄存器方式 | HAL 库方式 |
|--------|-----------|-----------|
| 时钟开启 | `RCC->APB1ENR \|= TIM6EN` | `MX_TIM6_Init()` 自动生成 |
| PSC 配置 | `TIM6->PSC = 7199` | CubeMX 配置 + 函数初始化 |
| ARR 配置 | `TIM6->ARR = 9999` | CubeMX 配置 + 函数初始化 |
| 中断使能 | `TIM6->DIER \|= UIE` | `HAL_TIM_Base_Start_IT()` 自动 |
| NVIC 配置 | 手动 `NVIC_EnableIRQ` | CubeMX 自动生成 |
| CEN 开启 | `TIM6->CR1 \|= CEN` | `HAL_TIM_Base_Start_IT()` 自动 |
| 清除 UIF | 手动 `TIM6->SR &= ~UIF` | **HAL 自动清除** |
| 中断函数 | `TIM6_IRQHandler` 中手动判断 | HAL 分发 + **回调函数** |
| 用户代码 | 写在中断函数中 | 写在**回调函数**中 |
| 代码量 | 中等 | **更少** |

---

## 九、HAL 库定时器相关函数汇总

| 函数 | 功能 |
|------|------|
| `HAL_TIM_Base_Init()` | 初始化定时器基本参数 |
| `HAL_TIM_Base_Start()` | 启动定时器（轮询） |
| `HAL_TIM_Base_Start_IT()` | 启动定时器（中断） |
| `HAL_TIM_Base_Start_DMA()` | 启动定时器（DMA） |
| `HAL_TIM_Base_Stop()` | 停止定时器 |
| `HAL_TIM_Base_Stop_IT()` | 停止定时器（中断） |
| `HAL_TIM_IRQHandler()` | 通用中断处理（HAL 内部） |
| `HAL_TIM_PeriodElapsedCallback()` | 周期结束回调（**用户重写**） |

---

## 十、易错点

| 易错点 | 说明 |
|--------|------|
| 忘记调用 `HAL_TIM_Base_Start_IT()` | CubeMX 不会自动开启定时器（CEN=0） |
| 忘记判断 `htim->Instance` | 所有定时器共享回调函数，需区分 |
| 选错启动函数 | 中断方式用 `_Start_IT()`，不是 `_Start()` |
| 重写回调函数忘记加 `__weak` | HAL 库中已声明为 `__weak`，直接重写即可 |
| NVIC 未勾选 | CubeMX 中必须勾选 TIM6 global interrupt |