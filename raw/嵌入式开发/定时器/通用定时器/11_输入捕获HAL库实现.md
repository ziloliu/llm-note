# 通用定时器 TIM4 输入捕获 — HAL 库实现 笔记

---

## 一、CubeMX 配置

### 1.1 基础配置

| 配置项 | 设置 |
|--------|------|
| Debug | Serial Wire |
| RCC | HSE 外部高速晶振 |
| 时钟树 | HSE → PLL ×9 → 72MHz, APB1 /2 → 36MHz |
| Connectivity | USART1 异步模式（串口打印） |

### 1.2 TIM5 配置（PWM 输出 — 信号源）

| 配置项 | 值 | 说明 |
|--------|:--:|------|
| Clock Source | Internal Clock | 内部时钟 |
| Channel 2 | PWM Generation CH2 | PWM 输出 |
| Prescaler (PSC) | 7199 | 7200 分频 → 10kHz |
| Counter Mode | Up | 向上计数 |
| Counter Period (ARR) | 99 | 100 级 |
| Internal Clock Division | No Division | 不分频 |
| PWM Mode | Mode 1 | PWM 模式 1 |
| **Pulse (CCR)** | **60** | **不能为 0 或 100** |
| Output Compare Preload | Enable | 预装载使能 |
| CH Polarity | High | 高电平有效 |

> ⚠️ Pulse 不能为 0（无方波输出）或 100（恒高电平），否则无法检测周期。
> 
> PA1 自动配置为复用推挽输出。

### 1.3 TIM4 配置（输入捕获 — 测量端）

| 配置项 | 值 | 说明 |
|--------|:--:|------|
| Clock Source | Internal Clock | 内部时钟 |
| Channel 1 | Input Capture direct mode | 输入捕获（直连） |
| Prescaler (PSC) | **71** | 72 分频 → 1MHz → 1μs/次 |
| Counter Mode | Up | 向上计数 |
| Counter Period (ARR) | 65535 | 最大值 |
| Internal Clock Division | No Division | 不分频 |
| Polarity | **Rising Edge** | 上升沿捕获 |
| IC Selection | **Direct** | 直连模式 |
| IC Prescaler | No Division | 不分频 |
| IC Filter | 0 | 不滤波 |

### 1.4 引脚重映射问题

```
默认情况：TIM4_CH1 被映射到 PD12（重映射）
实际需要：TIM4_CH1 应在 PB6（默认复用）

原因：HAL 库认为 PB6 优先用于 I2C1_SCL
     → 自动将 TIM4_CH1 重映射到 PD12

解决方法：
  ① 在芯片引脚图中找到 PD12 → Reset 释放
  ② 找到 PB6 → 选择 TIM4_CH1 功能
  ③ 回到 TIM4 页面重新勾选 Channel 1
  ④ 确认 PB6 变绿（可用状态）
```

### 1.5 NVIC 配置

| 配置项 | 设置 |
|--------|------|
| TIM4 global interrupt | ✅ 勾选 |
| 优先级 | 默认（无需修改，只有这一个中断） |

---

## 二、TIM5 PWM 输出参数

| 参数 | 值 | 计算 |
|------|:--:|------|
| 计数频率 | 10kHz | 72MHz / 7200 |
| PWM 频率 | **100Hz** | 10kHz / 100 |
| PWM 周期 | **10ms** | 1 / 100Hz |
| 占空比 | **60%** | CCR = 60, ARR = 99 |

---

## 三、TIM4 输入捕获参数

| 参数 | 值 | 计算 |
|------|:--:|------|
| 计数频率 | **1MHz** | 72MHz / 72 |
| 计数周期 | **1μs** | 1 / 1MHz |
| 最大可测周期 | 65535μs | ARR = 65535 |
| 最小可测频率 | 15.26Hz | 1 / 65.535ms |

---

## 四、HAL 库关键函数

### 4.1 启动函数

```c
// 启动 TIM5 PWM 输出
HAL_TIM_PWM_Start(&htim5, TIM_CHANNEL_2);

// 启动 TIM4 输入捕获（带中断）
HAL_TIM_IC_Start_IT(&htim4, TIM_CHANNEL_1);
```

| 函数 | 功能 | 本实验 |
|------|------|:------:|
| `HAL_TIM_PWM_Start()` | 启动 PWM 输出 | TIM5 ✅ |
| `HAL_TIM_IC_Start()` | 启动输入捕获（轮询） | — |
| `HAL_TIM_IC_Start_IT()` | 启动输入捕获（中断） | TIM4 ✅ |
| `HAL_TIM_IC_Start_DMA()` | 启动输入捕获（DMA） | — |

### 4.2 设置/获取比较值

```c
// 设置 CCR 值（写入）
__HAL_TIM_SET_COMPARE(&htim4, TIM_CHANNEL_1, value);

// 获取 CCR 值（读取）
__HAL_TIM_GET_COMPARE(&htim4, TIM_CHANNEL_1);
```

> 输入捕获和输出比较共用同一个 CCR 寄存器，函数通用。

### 4.3 设置计数器值

```c
// 将计数器清零
__HAL_TIM_SET_COUNTER(&htim4, 0);
```

---

## 五、输入捕获中断回调函数

### 5.1 查找回调函数

```
TIM4_IRQHandler
    → HAL_TIM_IRQHandler
        → HAL_TIM_IC_CaptureCallback()    ← 输入捕获回调
        → HAL_TIM_PeriodElapsedCallback() ← 更新（溢出）回调
```

> `HAL_TIM_IC_CaptureCallback` 是 `__weak` 弱定义函数，可重写。

### 5.2 回调函数实现

```c
void HAL_TIM_IC_CaptureCallback(TIM_HandleTypeDef *htim)
{
    if (htim->Instance == TIM4)
    {
        __HAL_TIM_SET_COUNTER(htim, 0);    // 清零计数器
    }
}
```

### 5.3 回调判断逻辑

```
进入中断 → HAL_TIM_IRQHandler → 识别为输入捕获事件
    → 调用 HAL_TIM_IC_CaptureCallback
        → 判断 htim->Instance == TIM4
            → 清零计数器 CNT = 0

关键：判断 htim->Instance 是哪个定时器
     因为所有定时器共用同一个回调函数入口
```

---

## 六、封装获取周期/频率函数

### 6.1 函数声明（tim.h）

```c
/* USER CODE BEGIN Prototypes */
double TIM4_GetPWMPeriod(void);
double TIM4_GetPWMFrequency(void);
/* USER CODE END Prototypes */
```

### 6.2 函数实现（tim.c）

```c
/* USER CODE BEGIN 1 */

/**
 * @brief  获取 PWM 信号周期（单位：ms）
 */
double TIM4_GetPWMPeriod(void)
{
    return (double)__HAL_TIM_GET_COMPARE(&htim4, TIM_CHANNEL_1) / 1000.0;
}

/**
 * @brief  获取 PWM 信号频率（单位：Hz）
 */
double TIM4_GetPWMFrequency(void)
{
    uint32_t ccr = __HAL_TIM_GET_COMPARE(&htim4, TIM_CHANNEL_1);
    if (ccr == 0)
        return 0;
    return 1000000.0 / (double)ccr;
}

/* USER CODE END 1 */
```

> 使用 `__HAL_TIM_GET_COMPARE` 读取 CCR1 值（与输出比较共用函数）。

---

## 七、主函数实现

### 7.1 重写 fputc（串口重定向）

```c
// usart.c 中添加
#include <stdio.h>

int fputc(int ch, FILE *f)
{
    HAL_UART_Transmit(&huart1, (uint8_t *)&ch, 1, 1000);
    return ch;
}
```

### 7.2 main.c 完整代码

```c
#include "main.h"
#include "tim.h"
#include "usart.h"
#include <stdio.h>

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_USART1_UART_Init();
    MX_TIM4_Init();
    MX_TIM5_Init();

    /* 启动 TIM5 PWM 输出（信号源） */
    HAL_TIM_PWM_Start(&htim5, TIM_CHANNEL_2);

    /* 启动 TIM4 输入捕获（带中断） */
    HAL_TIM_IC_Start_IT(&htim4, TIM_CHANNEL_1);

    printf("Hello World!\n");

    while (1)
    {
        printf("T=%.2fms, F=%.2fHz\n",
               TIM4_GetPWMPeriod(),
               TIM4_GetPWMFrequency());

        HAL_Delay(1000);
    }
}
```

---

## 八、运行结果

```
Hello World!
T=10.00ms, F=100.00Hz
T=10.00ms, F=100.00Hz
T=10.00ms, F=100.00Hz
...
```

```
TIM5 输出：PSC=7199, ARR=99 → PWM 频率=100Hz, 周期=10ms
TIM4 测量：CCR1 ≈ 10000 → 周期≈10ms, 频率≈100Hz ✅
```

---

## 九、GPIO 引脚映射总结

| 功能 | 默认引脚 | 重映射引脚 | 本实验 |
|------|:--------:|:----------:|:------:|
| TIM5_CH2 | **PA1** | — | ✅ PWM 输出 |
| TIM4_CH1 | **PB6** | PD12 | ✅ 输入捕获 |
| I2C1_SCL | **PB6** | — | 不使用 |

```
PB6 有两个复用功能：
  → TIM4_CH1（默认复用）
  → I2C1_SCL（默认复用，HAL 优先选择）

HAL 库优先将 PB6 分配给 I2C1
  → 将 TIM4_CH1 重映射到 PD12

解决：手动在引脚图中将 PB6 分配给 TIM4_CH1
```

---

## 十、寄存器方式 vs HAL 库方式对比

| 对比项 | 寄存器方式 | HAL 库方式 |
|--------|-----------|-----------|
| GPIO 配置 | 手动 CRL 位操作 | CubeMX 自动配置（注意重映射） |
| CCMR1 配置 | 手动 CC1S/IC1F/IC1PSC | CubeMX 自动生成 |
| CCER 配置 | 手动 CC1P/CC1E | CubeMX 自动生成 |
| DIER 配置 | 手动 CC1IE | CubeMX + NVIC 勾选 |
| NVIC 配置 | 手动代码 | CubeMX 勾选 |
| 启动 PWM | `CR1.CEN=1` | `HAL_TIM_PWM_Start()` |
| 启动捕获 | `CR1.CEN=1` | `HAL_TIM_IC_Start_IT()` |
| 读取 CCR | `TIM4->CCR1` | `__HAL_TIM_GET_COMPARE()` |
| 清零 CNT | `TIM4->CNT = 0` | `__HAL_TIM_SET_COUNTER(&htim4, 0)` |
| 中断处理 | `TIM4_IRQHandler` | `HAL_TIM_IC_CaptureCallback()` |
| 代码量 | 较多 | **更少** |

---

## 十一、HAL 库中输入捕获的中断回调链

```
硬件触发捕获中断
    │
    ↓
TIM4_IRQHandler()                    ← it.c 中
    │
    ↓
HAL_TIM_IRQHandler(&htim4)           ← HAL 库内部
    │
    ├── 识别中断源为输入捕获
    │
    ↓
HAL_TIM_IC_CaptureCallback(&htim4)   ← 可重写的回调函数
    │
    ↓
用户代码：判断 Instance + 清零 CNT
```

---

## 十二、配置注意事项

| 注意事项 | 说明 |
|----------|------|
| **CCR 不能为 0 或 100%** | 否则无方波输出，无法检测周期 |
| **PB6 重映射问题** | HAL 库默认映射到 PD12，需手动改回 PB6 |
| **捕获中断使能** | CubeMX 中必须勾选 TIM4 global interrupt |
| **PSC = 71** | 72 分频 → 1MHz → 1μs 精度 |
| **ARR = 65535** | 最大值，避免溢出 |
| **回调函数判断 Instance** | 所有定时器共用同一回调入口 |