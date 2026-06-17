# PWM 输入模式 — HAL 库实现（测周期、频率、占空比） 笔记

---

## 一、实验概述

| 项目 | 说明 |
|------|------|
| TIM5 | PWM 输出（信号源）→ PA1（CH2） |
| TIM4 | PWM 输入捕获（检测）→ PB6（CH1） |
| 测量内容 | 周期、频率、**占空比** |
| 实现方式 | HAL 库（CubeMX 配置） |
| 硬件连接 | PA1 跳线到 PB6 |

---

## 二、CubeMX 配置

### 2.1 基础配置

| 配置项 | 设置 |
|--------|------|
| Debug | Serial Wire |
| RCC | HSE 外部高速晶振 |
| 时钟树 | HSE → PLL ×9 → 72MHz, APB1 /2 → 36MHz |
| Connectivity | USART1 异步模式 |

### 2.2 TIM5 配置（PWM 输出）

| 配置项 | 值 | 说明 |
|--------|:--:|------|
| Clock Source | Internal Clock | 内部时钟 |
| Channel 2 | PWM Generation CH2 | PWM 输出 |
| Prescaler (PSC) | 7199 | 7200 分频 → 10kHz |
| Counter Mode | Up | 向上计数 |
| Counter Period (ARR) | 99 | 100 级 |
| **Pulse (CCR)** | **60** | **不能为 0 或 100** |
| PWM Mode | Mode 1 | PWM 模式 1 |
| CH Polarity | High | 高电平有效 |

### 2.3 TIM4 配置（PWM 输入模式 — 核心）

#### 基本时基设置

| 配置项 | 值 | 说明 |
|--------|:--:|------|
| **Slave Mode** | **Reset Mode** | 从模式：复位模式 |
| **Trigger Source** | **TI1FP1** | 触发源：通道 1 信号 |
| **Clock Source** | **Internal Clock** | 计数时钟：内部时钟 |
| **Channel 1** | **Input Capture direct mode** | 直连模式 |
| **Channel 2** | **Input Capture indirect mode** | 交叉模式 |
| Prescaler (PSC) | **71** | 72 分频 → 1MHz（1μs 精度） |
| Counter Mode | Up | 向上计数 |
| Counter Period (ARR) | 65535 | 最大值 |

#### 通道配置

| 配置项 | 通道 1 | 通道 2 |
|--------|:------:|:------:|
| Polarity | **Rising Edge** | **Falling Edge** |
| IC Selection | **Direct** | **Indirect** |
| IC Prescaler | No Division | No Division |
| IC Filter | 0 | 0 |

#### CubeMX 配置界面

```
TIM4 配置页面：

Slave Mode:           [Reset Mode]           ← 从模式：复位
Trigger Source:       [TI1FP1]               ← 触发源
Clock Source:         [Internal Clock]       ← 内部时钟

Channel 1:            [Input Capture direct mode]
  Polarity:           Rising Edge            ← 上升沿

Channel 2:            [Input Capture indirect mode]
  Polarity:           Falling Edge           ← 下降沿
```

### 2.4 NVIC 配置

```
本实验不使用中断（从模式硬件自动复位）
→ NVIC 无需更改
```

---

## 三、GPIO 重映射处理

```
CubeMX 默认将 TIM4_CH1 映射到 PD12（重映射）
实际需要 PB6（默认复用）

原因：PB6 同时是 I2C1_SCL 的默认复用引脚
     HAL 库优先将 PB6 分配给 I2C1

解决步骤：
  ① GPIO 页面找到 PD12 → Reset 释放
  ② 找到 PB6 → 选择 TIM4_CH1
  ③ 回到 TIM4 页面重新配置：
     - Slave Mode = Reset Mode
     - Trigger Source = TI1FP1
     - Clock Source = Internal Clock
     - Channel 1 = Input Capture direct mode
     - Channel 2 = Input Capture indirect mode
  ④ 重新配置通道极性（会被重置）
  ⑤ 确认 PB6 引脚变绿 ✅
```

---

## 四、滤波器配置说明

```
信号从 CH1 引脚输入后：

CH1 引脚 → 滤波器（只配一次）→ 分成两路
                                    │
                    ┌───────────────┼───────────────┐
                    ↓                               ↓
              上升沿检测                      下降沿检测
            (边沿检测器 1)                  (边沿检测器 2)
                    │                               │
                    ↓                               ↓
               TI1FP1 → CCR1                  TI2FP2 → CCR2
              (周期 T)                      (高电平时间 t)

滤波器：只配一次（在输入端）
边沿检测器：需要两个（不同极性）
```

> CubeMX 配置页面中通道 2 没有滤波器选项，正是因为滤波器只在输入端配置一次。

---

## 五、HAL 库关键函数

### 5.1 启动函数

```c
// TIM5 PWM 输出
HAL_TIM_PWM_Start(&htim5, TIM_CHANNEL_2);

// TIM4 输入捕获（两个通道都必须开启）
HAL_TIM_IC_Start(&htim4, TIM_CHANNEL_1);    // 通道 1
HAL_TIM_IC_Start(&htim4, TIM_CHANNEL_2);    // 通道 2
```

### 5.2 读取 CCR 值

```c
__HAL_TIM_GET_COMPARE(&htim4, TIM_CHANNEL_1);    // 读 CCR1（周期）
__HAL_TIM_GET_COMPARE(&htim4, TIM_CHANNEL_2);    // 读 CCR2（高电平时间）
```

---

## 六、封装自定义函数

### 6.1 函数声明（tim.h）

```c
/* USER CODE BEGIN Prototypes */
double TIM4_GetPWMPeriod(void);
double TIM4_GetPWMFrequency(void);
double TIM4_GetPWMDutyCycle(void);
/* USER CODE END Prototypes */
```

### 6.2 函数实现（tim.c）

```c
/* USER CODE BEGIN 1 */

double TIM4_GetPWMPeriod(void)
{
    return (double)__HAL_TIM_GET_COMPARE(&htim4, TIM_CHANNEL_1) / 1000.0;
}

double TIM4_GetPWMFrequency(void)
{
    uint32_t ccr1 = __HAL_TIM_GET_COMPARE(&htim4, TIM_CHANNEL_1);
    if (ccr1 == 0)
        return 0;
    return 1000000.0 / (double)ccr1;
}

double TIM4_GetPWMDutyCycle(void)
{
    uint32_t ccr1 = __HAL_TIM_GET_COMPARE(&htim4, TIM_CHANNEL_1);
    if (ccr1 == 0)
        return 0;
    return (double)__HAL_TIM_GET_COMPARE(&htim4, TIM_CHANNEL_2) * 1.0
         / (double)ccr1;
}

/* USER CODE END 1 */
```

### 6.3 占空比计算说明

```
占空比 = CCR2 / CCR1

CCR2 = 高电平时间（μs）
CCR1 = 周期（μs）

CCR2 和 CCR1 都是 uint32_t
直接整数除法会丢失小数
→ 乘以 1.0 强制转为浮点运算
→ 结果为 0.0 ~ 1.0（小数形式）
→ printf 中乘以 100 转为百分数
```

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

    printf("Hello World!\n");

    /* 启动 TIM5 PWM 输出 */
    HAL_TIM_PWM_Start(&htim5, TIM_CHANNEL_2);

    /* 启动 TIM4 输入捕获（两个通道都必须开启） */
    HAL_TIM_IC_Start(&htim4, TIM_CHANNEL_1);    // 通道 1：上升沿
    HAL_TIM_IC_Start(&htim4, TIM_CHANNEL_2);    // 通道 2：下降沿

    while (1)
    {
        printf("T=%.2fms, F=%.2fHz, D=%.2f%%\n",
               TIM4_GetPWMPeriod(),
               TIM4_GetPWMFrequency(),
               TIM4_GetPWMDutyCycle() * 100);

        HAL_Delay(1000);
    }
}
```

---

## 八、运行结果

```
Hello World!
T=10.00ms, F=100.00Hz, D=60.00%
T=10.00ms, F=100.00Hz, D=60.00%
T=10.00ms, F=100.00Hz, D=60.00%
...
```

```
TIM5：PSC=7199, ARR=99, CCR=60
  → PWM 频率 = 100Hz
  → 周期 = 10ms
  → 占空比 = 60%

TIM4 测量：
  CCR1 ≈ 10000 → 周期 ≈ 10ms ✅
  CCR2 ≈ 6000  → 高电平 ≈ 6ms ✅
  占空比 ≈ 60% ✅
```

---

## 九、寄存器方式 vs HAL 库方式对比

| 对比项 | 寄存器方式 | HAL 库方式 |
|--------|-----------|-----------|
| 时钟开启 | 手动 RCC 位操作 | CubeMX 自动生成 |
| GPIO 配置 | 手动 CRL 位操作 | CubeMX（注意重映射） |
| SMCR 配置 | 手动 TS/SMS 位操作 | CubeMX 下拉选择 |
| CCMR 配置 | 手动 CCxS/ICxPSC 位操作 | CubeMX Direct/Indirect |
| CCER 配置 | 手动 CCxP/CCxE 位操作 | CubeMX Rising/Falling |
| 启动定时器 | `CR1.CEN = 1` | `HAL_TIM_IC_Start()` × 2 |
| 读取 CCR | `TIM4->CCR1` / `TIM4->CCR2` | `__HAL_TIM_GET_COMPARE()` |
| 中断 | 不需要 | 不需要 |
| 代码量 | 较多（初始化复杂） | **较少（图形化配置）** |

---

## 十、CubeMX 配置与寄存器对照

| CubeMX 配置 | 寄存器 | 值 | 说明 |
|-------------|--------|:--:|------|
| Slave Mode = Reset Mode | SMCR.SMS | **100** | 复位模式 |
| Trigger Source = TI1FP1 | SMCR.TS | **101** | 触发源选择 |
| Clock Source = Internal | — | — | 内部时钟 |
| CH1 = Direct mode | CCMR1.CC1S | **01** | 直通 |
| CH1 Polarity = Rising | CCER.CC1P | **0** | 上升沿 |
| CH2 = Indirect mode | CCMR1.CC2S | **10** | 交叉 |
| CH2 Polarity = Falling | CCER.CC2P | **1** | 下降沿 |
| CH1 Enable | CCER.CC1E | **1** | 通道 1 使能 |
| CH2 Enable | CCER.CC2E | **1** | 通道 2 使能 |
| PSC = 71 | TIM4->PSC | **71** | 1MHz |
| ARR = 65535 | TIM4->ARR | **65535** | 最大值 |

---

## 十一、定时器启动顺序

```
⚠️ 必须同时启动两个通道的输入捕获：

HAL_TIM_IC_Start(&htim4, TIM_CHANNEL_1);    // 通道 1（上升沿）
HAL_TIM_IC_Start(&htim4, TIM_CHANNEL_2);    // 通道 2（下降沿）

缺少任何一个都会导致测量失败：
  → 只开通道 1：CCR1 正常，CCR2 始终为 0 → 占空比 = 0%
  → 只开通道 2：CCR2 可能正常，CCR1 始终为 0 → 所有结果异常
```

---

## 十二、完整执行流程

```
系统上电
    │
    ├── HAL_Init()
    ├── SystemClock_Config() → 72MHz
    ├── MX_GPIO_Init()
    ├── MX_USART1_UART_Init()
    ├── MX_TIM4_Init() → PWM 输入模式
    │   ├── Slave Mode = Reset Mode
    │   ├── Trigger Source = TI1FP1
    │   ├── Clock Source = Internal Clock
    │   ├── CH1: Direct, Rising Edge
    │   └── CH2: Indirect, Falling Edge
    ├── MX_TIM5_Init() → PWM 输出
    │   ├── PSC=7199, ARR=99
    │   ├── CCR=60（占空比 60%）
    │   └── PWM Mode 1
    │
    ├── printf("Hello World!\n")
    ├── HAL_TIM_PWM_Start(&htim5, TIM_CHANNEL_2)
    ├── HAL_TIM_IC_Start(&htim4, TIM_CHANNEL_1)
    ├── HAL_TIM_IC_Start(&htim4, TIM_CHANNEL_2)
    │
    └── 主循环：
        ├── printf 周期/频率/占空比
        └── HAL_Delay(1000)
```

---

## 十三、常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 占空比始终为 0 | 通道 2 未启动 | 确认两个通道都调用 `HAL_TIM_IC_Start` |
| 占空比始终为 0 | CH2 未配为 Indirect | CubeMX 检查 Channel 2 选择 |
| 占空比始终为 0 | CH2 极性未选 Falling | CubeMX 确认下降沿 |
| 所有结果为 0 | 引脚映射到 PD12 | 手动改回 PB6 |
| 所有结果为 0 | SMCR 未配 | 确认 Slave Mode = Reset Mode |
| 所有结果为 0 | TIM5 占空比 0% 或 100% | 改为中间值（如 60） |
| 周期正常占空比异常 | 只开了通道 1 未开通道 2 | 补上通道 2 的启动 |
| 滤波器只配一个 | 正常 | 滤波器在输入端只配一次 |

---

## 十四、三种方案对比总结

| 方案 | 周期 | 频率 | 占空比 | 中断 | 全局变量 | 精度 |
|------|:----:|:----:|:------:|:----:|:--------:|:----:|
| 中断状态机（count） | ✅ | ✅ | ❌ | ✅ | ✅ | 一般 |
| 中断优化（每次清零） | ✅ | ✅ | ❌ | ✅ | ❌ | 较好 |
| **PWM 输入模式** | **✅** | **✅** | **✅** | **❌** | **❌** | **最高** |